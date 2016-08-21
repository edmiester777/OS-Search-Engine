import re
import searchengine.debugtools
import urllib.request
import time
import pysolr
import multiprocessing
import searchengine.solr_tools
from datetime import date, timedelta
from os import path
from urllib.parse import urlparse, urlsplit, quote, urlunsplit
from concurrent.futures import ProcessPoolExecutor
from searchengine.manager.managers import ClientManager
from searchengine.compression.compressionhelper import CompressionHelper
from searchengine.webcrawler.parser import Parser

TLD_LIST_URL = "https://publicsuffix.org/list/effective_tld_names.dat"

##
# @class    CrawlerExecutor
#
# @brief    A child class of ThreadPoolExecutor
#           This class is used to control our multithreading webcrawler architecture.
#           Handles dispatching tasks to each of our webcrawlers.
#           (modified by Intricate 6/18/2016 - heavily based on original SwarmController by Edward Callahan)
#
# @author   Edward Callahan
# @date 6/13/2016
class CrawlerExecutor(ProcessPoolExecutor):
    def __init__(self, crawler_type = None, max_workers = None, ip_address = 'localhost', port = 4948, authkey = None):
        self.crawler_type = crawler_type
        self.ip_address = ip_address
        self.port = port
        self.authkey = authkey
        return super().__init__(max_workers)

    ##
    # @fn   execute_tasks(self)
    #
    # @brief    Executes the tasks operation.
    #
    # @author   Edward Callahan
    # @date 6/13/2016
    #
    # @param    self    The class instance that this method operates on.
    #
    # @return   A value.
    def execute_tasks(self):
        manager = ClientManager(self.ip_address, self.port, self.authkey)
        lock = manager.Lock()
        for i in range(self._max_workers):
            crawler = self.crawler_type(i, download_images = False)
            self.submit(crawler.run, lock)
        self.shutdown(wait = True)

    ##
    # @fn   parse_url(self, url, currentUrl)
    #
    # @brief    Parse URL.
    #
    # @author   Edward Callahan
    # @date 6/12/2016
    #
    # @param    self        The class instance that this method operates on.
    # @param    url         URL of the image.
    # @param    currentUrl  Current URL being crawled.
    #
    # @return    Parsed url.
    def parse_url(self, url, currentUrl):

        ##############################################################
        # Not yet implemented:
        ##############################################################
        # Check for <base> tag to see where relative paths point to.
        # 
        ##############################################################



        if url is None:
            return ""
        parsedUrl = urlparse(currentUrl)
        url = url.replace(" ", "%20") #< Getting rid of pesky spaces that happen during decode
        newUrl = None
        # Checking if url is not absolute
        if not url.startswith("http://") and not url.startswith("https://"):
            if url.startswith("/"):
                # Url references root of url (this makes replacing it easy on us)
                if url.startswith("//"): #< refrencing https connection
                    newUrl = url.replace("//", "http://", 1)
                else:
                    newUrl = parsedUrl.scheme + url
            else:
                # Url references a relative directory or file.
                regex = re.compile("(http[s]?)[/\\\\]+")
                if regex.match(url):
                    newUrl = regex.sub("<1>://", url)
                else:
                    newUrl = parsedUrl.scheme + path.dirname(parsedUrl.path) + "/" + url
        # Now we check for http/+ or https/+ urls
        else:
            newUrl = url

        # Checking if url has any anchors
        if newUrl.find("#") != -1:
            split = newUrl.split("#")
            newUrl = split[0]

        # Trimming slashes
        while(newUrl.endswith("/")):
            newUrl = newUrl[:-1]
        return newUrl


##
# @class    WebCrawler
#
# @brief    Entity used to crawl through urls and parse them to find and save data.
#           (modified by Intricate 6/18/2016 - heavily based on original WebCrawler)
#
# @author   Edward Callahan
# @date 6/12/2016
class WebCrawler(Parser):

    ##
    # @fn   __init__(self, id, download_images = False)
    #
    # @brief    Class initializer.
    #
    # @author   Edward Callahan
    # @date 6/13/2016
    #
    # @param    self                        The class instance that this method operates on.
    # @param    id                          The identifier.
    # @param    optional download_images    The download images.
    def __init__(self, id, download_images = False):
        Parser.__init__(self)
        self.id = id
        self.download_images = download_images
        self.current_url = None
        self.meta_title = ""
        self.meta_description = ""
        self.meta_keywords = ""
        self.title = ""
        self.content = ""
        self.future_urls = []
        self.found_urls = []
        self.lock = None
        self.tld_list = []
        self.solr_working = None
        self.solr_main = None
        

    ##
    # @fn   __clean_string(self, string)
    #
    # @brief    Clean a string of uneeded white space or "\n" characters embedded in text.
    #           Also cleans XML or HTML tags in string.
    #
    # @author   Edward Callahan
    # @date 8/13/2016
    #
    # @param    self    The class instance that this method operates on.
    # @param    string  The string.
    def __clean_string(self, string):
        string = re.sub('[\s|\\n]+', ' ', string)
        string = re.sub('<[^>]*>', '', string)
        return string


    ##
    # @fn   run(self, lock)
    #
    # @brief    Loop that is used to crawl through the web.
    #
    # @author   Edward Callahan
    # @date 6/13/2016
    #
    # @param    self    The class instance that this method operates on.
    # @param    lock    Global synchronization lock.
    def run(self, lock):
        global TLD_LIST_URL
        self.lock = lock
        while(True):
            if self.solr_working is None:
                self.solr_working = searchengine.solr_tools.get_solr_instance('working', self.id)
            if self.solr_main is None:
                self.solr_main = searchengine.solr_tools.get_solr_instance('main', self.id)
            # Loading TLD list
            if len(self.tld_list) == 0:
                searchengine.debugtools.log("[WC:{}] Loading TLD list...".format(str(self.id)))
                response = urllib.request.urlopen(TLD_LIST_URL)
                full_text_list = response.read().decode()
                tmp_tld_list = [s.strip() for s in full_text_list.splitlines()]
                self.tld_list = [tld for tld in tmp_tld_list if not tld.startswith('//') and not tld.startswith('*') and len(tld) > 0]
                continue
            
            try:
                self.current_url = self.get_url_to_crawl()

                if not self.current_url or self.current_url is None:
                    time.sleep(10)
                    continue
            except Exception as ex:
                searchengine.debugtools.log_exception(ex)
                time.sleep(10)
                continue

            try:
                searchengine.debugtools.log("[WC:"+ str(self.id) + "] Crawling url: " + self.current_url)

                req = urllib.request.Request(
                    self.current_url,
                    headers = {
                        "User-Agent" : "OS-SEARCH-ENGINE-CRAWLER"
                    }
                )
                response = urllib.request.urlopen(req)
                if self.current_url != response.geturl():
                    self.__delete_from_solr()
                    self.current_url = response.geturl()
                    self.current_url = self.parse_url2(self.current_url)
 
                data = response.read()
                html = data.decode("utf-8")
                self.feed(html)
                self.close()

                if len(self.future_urls) == 0:
                    self.__post_urls_to_solr()
                    self.found_urls.clear()
                self.content = " ".join(self.split_key_words(self.content))
                self.__post_content_to_solr()

                self.tagQueue.clear()
                self.meta_title = ""
                self.meta_description = ""
                self.meta_description = ""
                self.title = ""
                self.content = ""
            except Exception as ex:
                self.__delete_from_solr()
                searchengine.debugtools.log("[WC:"+ str(self.id) + "] Could not grab url: " + self.current_url)
                searchengine.debugtools.log_exception(ex)

    ##
    # @fn   parse_url2(self, resource_url)
    #
    # @brief    Parse URL.
    #
    # @author   Intricate
    # @date 6/18/2016
    #
    # @param    self            The class instance that this method operates on.
    # @param    resource_url    URL of the requested resource.
    #
    # @return    Parsed url.

    def parse_url2(self, resource_url):

        ##############################################################
        # TODO
        ##############################################################
        # Check for <base> tag to see where relative paths point to.
        # Filter out "javascript:*"
        # 
        ##############################################################
        if resource_url is None:
            return ""

        result_url = ""

        # percent encode urls - http://svn.python.org/view/python/trunk/Lib/urllib.py?r1=71780&r2=71779&pathrev=71780
        resource_url = quote(resource_url, safe="%/:=&?~#+!$,;'@()*[]")
        self.current_url = quote(self.current_url, safe="%/:=&?~#+!$,;'@()*[]")

        # split urls
        split_resource_url = urlsplit(resource_url)
        split_current_page_url = urlsplit(self.current_url)

        # does our res_url come with http:// or https:// scheme?
        if re.compile("^(http|https)").match(split_resource_url.scheme):
            result_url = urlunsplit(split_resource_url)
        else:
            if re.compile("^(/){2}").match(resource_url):
                result_url = split_current_page_url.scheme + ":" + resource_url
            elif re.compile("^(/)+").match(resource_url):
                result_url = split_current_page_url.scheme + "://" + split_current_page_url.hostname + resource_url
            elif resource_url.startswith("javascript:"):
                return ""
            else:
                result_url = urlunsplit(split_current_page_url) + (("/" + resource_url) if len(resource_url) > 0 else "")
        while(result_url.endswith('/')):
            result_url = result_url[:-1]
        return result_url

    ##
    # @fn   __post_content_to_solr(self)
    #
    # @brief    Posts data and content to solr.
    #
    # @author   Edward Callahan
    # @date 8/12/2016
    #
    # @param    self    The class instance that this method operates on.
    def __post_content_to_solr(self):
        if len(self.title) == 0 or len(self.content) == 0:
            return
        parsed = urlparse(self.current_url)
        is_https = parsed.scheme == "https"
        host = parsed.hostname
        while host.endswith('/'):
            host = host[:-1]
        subdomain = ""
        domain = host
        path = parsed.path
        this_tld = ""
        hostsplit = host.split('.')
        while path.endswith('/'):
            path = path[:-1]
        for i in range(1, len(hostsplit)):
            end = ".".join(hostsplit[i:])
            if end in self.tld_list:
                this_tld = end
                domain = hostsplit[:i][-1]
                subdomain = ".".join(hostsplit[:i-1])
                break
        doc = {
                "id"               : host + path,
                "meta_keywords"    : self.__clean_string(self.meta_keywords),
                "meta_description" : self.__clean_string(self.meta_description),
                "title"            : self.__clean_string(self.meta_title if len(self.meta_title) > 0 else self.title),
                "content"          : self.__clean_string(self.content),
                "is_https"         : is_https,
                "subdomain"        : subdomain,
                "domain"           : domain,
                "tld"              : this_tld,
                "path"             : path,
                "last_update_time" : int(time.time())
        }
        self.solr_working.add([doc], overwrite=True, commit=False)

    ##
    # @fn   split_key_words(self, orig_string)
    #
    # @brief    Get all valid words from the content string.
    #
    # @author   Edward Callahan
    # @date 6/17/2016
    #
    # @param    self        The class instance that this method operates on.
    # @param    orig_string The string to split.
    def split_key_words(self, orig_string):
        all_words = re.findall(r"\w+", orig_string)

        # Removing invalid words
        all_words = [word.lower() for word in all_words if re.match("[A-Za-z]", word)]

        return all_words

    ##
    # @fn   __post_urls_to_solr(self)
    #
    # @brief    Posts the parsed urls to solr (does not overwrite existing urls).
    #
    # @author   Edward Callahan
    # @date 8/12/2016
    #
    # @param    self    The class instance that this method operates on.
    def __post_urls_to_solr(self):
        if len(self.found_urls) == 0:
            return
        docs = []
        for url in self.found_urls:
            parsed = urlparse(url)
            is_https = parsed.scheme == "https"
            host = parsed.hostname
            path = parsed.path
            while host.endswith('/'):
                host = host[:-1]
            while path.endswith('/'):
                path = path[:-1]
            docs.append({
                "id"               : host + path,
                "is_https"         : is_https,
                "last_update_time" : 0
            })
        self.solr_working.add(docs, overwrite = False, commit=True)

    ##
    # @fn   __delete_from_solr(self)
    #
    # @brief    Delete this url from solr.
    #
    # @author   Edward Callahan
    # @date 8/13/2016
    #
    # @param    self    The class instance that this method operates on.
    def __delete_from_solr(self):
        parsed = urlparse(self.current_url)
        host = parsed.hostname
        path = parsed.path
        while host.endswith('/'):
            host = host[:-1]
        while path.endswith('/'):
            path = path[:-1]
        self.solr_working.delete(host + path, commit=False)
        self.solr_main.delete(host + path, commit=True)

    ##
    # @fn   validate_url(self, url)
    #
    # @brief    Validates the URL.
    #
    # @author   Edward Callahan
    # @date 6/12/2016
    #
    # @param    self    The class instance that this method operates on.
    # @param    url     URL to validate.
    #
    # @return True if url is valid, else False.
    def validate_url(self, url):
        url = str(url) #< ensuring url is string
        regex = re.compile("[http|https]+:\/\/[^.]+\.[A-Za-z]+")
        return regex.match(url)

    ##
    # @fn   add_url(self, url)
    #
    # @brief    Adds a URL to our list to be crawled if it has not been crawled yet.
    #
    # @author   Edward Callahan
    # @date 6/12/2016
    #
    # @param    self    The class instance that this method operates on.
    # @param    url     URL to be added.
    def add_url(self, url):
        # url validation
        if not self.validate_url(url):
            return

        # Checking if url is of any disallowed types
        parsed = urlparse(url)
        path_split = parsed.path.split("/")
        if path_split[-1].find(".") != -1:
            # Path contains file type... checking against allowed filetypes
            allowed_types = [
                "asp",
                "aspx",
                "axd",
                "asx",
                "asmx",
                "ashx",
                "cfm",
                "yaws",
                "html",
                "htm",
                "xhtml",
                "jhtml",
                "jsp",
                "jspx",
                "wss",
                "do",
                "action"
                "pl",
                "php",
                "php4",
                "php3",
                "phtml",
                "py",
                "rb",
                "rhtml",
                "xml",
                "rss",
                "cgi",
            ]
            file_type = path_split[-1].split(".")
            if file_type[-1] not in allowed_types:
                return
        if url not in self.found_urls:
            self.found_urls.append(url)

    ##
    # @fn   get_url_to_crawl(self)
    #
    # @brief    Gets URL to crawl.
    #
    # @author   Edward Callahan
    # @date 6/13/2016
    #
    # @param    self    The class instance that this method operates on.
    def get_url_to_crawl(self):
        # Querying database for url to crawl
        if len(self.future_urls) == 0:
            with self.lock:
                response = self.solr_working.search("last_update_time:[0 TO " + str(int(time.time() - (60 * 60 * 24 * 7))) + "]", rows=20)
                if len(response.docs) == 0:
                    return False
                doc_updates = []
                for doc in response.docs:
                    doc_updates.append({
                        "id"               : doc["id"],
                        "last_update_time" : int(time.time())
                    })
                    self.future_urls.append("http" + ("s" if doc["is_https"] else "") + "://" + doc["id"])
                self.solr_working.add(doc_updates)
        next_url = self.future_urls.pop(0)
        return next_url

    ##
    # @fn   found_url(self, url)
    #
    # @brief    Override from Parser.
    #
    # @author   Edward Callahan
    # @date 6/12/2016
    #
    # @param    self    The class instance that this method operates on.
    # @param    url     URL that was located.
    def found_url(self, url):
        url = self.parse_url2(url)
        self.add_url(url)

    ##
    # @fn   found_image(self, url)
    #
    # @brief    Found image url.
    #
    # @author   Edward Callahan
    # @date 6/12/2016
    #
    # @param    self    The class instance that this method operates on.
    # @param    url     The image.
    def found_image(self, url):
        if not self.download_images:
            return
        url = self.parse_url2(url)
        if self.validate_url(url):
            if self.crawler_executor.has_image_been_downloaded(url):
                return
            searchengine.debugtools.log("[WC:"+ str(self.id) + "] Downloading image from: " + url)
            try:
                if not path.isdir(searchengine.debugtools.debug_outfile + "/image_downloads"):
                    os.makedirs(__HERE__ + "/image_downloads")
                self.crawler_executor.add_downloaded_image(url)
                urllib.request.urlretrieve(url,  __HERE__ + "/image_downloads/" + urllib.parse.quote_plus(url.split("/")[-1]))
            except Exception as ex:
                searchengine.debugtools.log("[WC:"+ str(self.id) + "] Failed to download image: " + str(ex))

    ##
    # @fn   foundContent(self, content)
    #
    # @brief    Override from parser.
    #
    # @author   Edward Callahan
    # @date 6/16/2016
    #
    # @param    self    The class instance that this method operates on.
    # @param    content The content.
    def found_content(self, content):
        self.content += content

    ##
    # @fn   found_title(self, title)
    #
    # @brief    Override from parser.
    #
    # @author   Edward Callahan
    # @date 6/20/2016
    #
    # @param    self    The class instance that this method operates on.
    # @param    title   The title.
    def found_title(self, title):
        self.title += title

    ##
    # @fn   found_meta_name_content_pair(self, name, content)
    #
    # @brief    Override from Parser.
    #
    # @author   Edward Callahan
    # @date 6/21/2016
    #
    # @param    self    The class instance that this method operates on.
    # @param    name    The name.
    # @param    content The content.
    def found_meta_name_content_pair(self, name, content):
        if name == "title":
            self.meta_title = content
        elif name == "description":
            self.meta_description = content
        elif name == "keywords":
            self.meta_keywords = content