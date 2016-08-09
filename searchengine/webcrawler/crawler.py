import re
import searchengine.debugtools
import urllib.request
import time
from os import path
from threading import Lock
from urllib.parse import urlparse, urlsplit, quote, urlunsplit
from concurrent.futures import ThreadPoolExecutor
from searchengine.compression.compressionhelper import CompressionHelper
from searchengine.database.connector import DatabaseConnector
from searchengine.webcrawler.parser import Parser

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
class CrawlerExecutor(ThreadPoolExecutor):
    def __init__(self, crawler_type = None, max_workers = None):
        self.mtx = Lock()
        self.crawler_type = crawler_type
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
        for i in range(self._max_workers):
            crawler = self.crawler_type(self, i, download_images = False)
            self.submit(crawler.run)
        self.shutdown(wait = True)


    ##
    # @fn   parse_url2(self, resource_url, curren_page_url)
    #
    # @brief    Parse URL
    #
    # @author   Intricate
    # @date     6/18/2016
    #
    # @param    self            The class instance that this method operates on.
    # @param    resource_url    URL of the requested resource.
    # @param    currentUrl      Current URL being crawled.
    #
    # @return    Parsed url.
    def parse_url2(self, resource_url, current_page_url):

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
        current_page_url = quote(current_page_url, safe="%/:=&?~#+!$,;'@()*[]")

        # split urls
        split_resource_url = urlsplit(resource_url)
        split_current_page_url = urlsplit(current_page_url)

        # does our res_url come with http:// or https:// scheme?
        if re.compile("^(http|https)").match(split_resource_url.scheme):
            result_url = urlunsplit(split_resource_url)
        else:
            if re.compile("^(/){2}").match(resource_url):
                result_url = split_current_page_url.scheme + ":" + resource_url
            elif re.compile("^(/)+").match(resource_url):
                result_url = split_current_page_url.scheme + "://" + split_current_page_url.hostname + resource_url
            else:
                result_url = urlunsplit(split_current_page_url) + "/" + resource_url
        return result_url

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
    # @fn   get_domain_id_from_url(self, url)
    #
    # @brief    Gets domain identifier from URL.
    #
    # @author   Edward Callahan
    # @date 6/15/2016
    #
    # @param    self    The class instance that this method operates on.
    # @param    url     URL of the document.
    def get_domain_id_from_url(self, url):
        parsed = urlparse(url)
        if len(parsed.hostname) == 0:
            return None
        ret = DatabaseConnector.execute_query(
            """
            SELECT domain_id
            FROM domains
            WHERE domain_name = %s
            """,
            parsed.hostname
        )
        if len(ret) == 0:
            return None
        return ret[0]["domain_id"]


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
    # @fn   __init__(self, crawler_executor, run_condition, id, download_images = False)
    #
    # @brief    Class initializer.
    #
    # @author   Edward Callahan
    # @date 6/13/2016
    #
    # @param    self                        The class instance that this method operates on.
    # @param    crawler_executor            The CrawlerExecutor controlling this object.
    # @param    id                          The identifier.
    # @param    optional download_images    The download images.
    def __init__(self, crawler_executor, id, download_images = False):
        Parser.__init__(self)
        self.crawler_executor = crawler_executor
        self.id = id
        self.download_images = download_images
        self.path_id = None

    ##
    # @fn   run(self)
    #
    # @brief    Loop that is used to crawl through the web.
    #
    # @author   Edward Callahan
    # @date 6/13/2016
    #
    # @param    self    The class instance that this method operates on.
    def run(self):
        while(True):
            self.current_url = self.get_url_to_crawl()
            if self.current_url == False:
                time.sleep(10)
                continue

            searchengine.debugtools.log("[WC:"+ str(self.id) + "] Crawling url: " + self.current_url)
            try:
                response = urllib.request.urlopen(self.current_url, timeout=5)
                data = response.read()
                html = data.decode("utf-8")
                self.cache_page_data(self.current_url, data)
                self.feed(html)
                self.close()
            except Exception as ex:
                searchengine.debugtools.log("[WC:"+ str(self.id) + "] Could not grab url: " + self.current_url)
                searchengine.debugtools.log_exception(ex)

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

        # Calling procedure to add url.
        is_https = 0 if parsed.scheme == "https" else 1
        host = parsed.hostname
        path = parsed.path 
        DatabaseConnector.call_procedure("ADD_URL", is_https, host, path)

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
        response = DatabaseConnector.call_procedure("GET_URL_TO_CRAWL", 0, '', 0, '')
        if response == False or response[0] is None:
            self.path_id = None
            return False
        rel = "http" + ("s" if int(response[0]) == 1 else "") + "://" + response[1] + response[3]
        self.path_id = response[2]
            
        return rel

    ##
    # @fn   cache_page_data(self, url, data)
    #
    # @brief    Cache data returned from page.
    #
    # @author   Edward Callahan
    # @date 6/15/2016
    #
    # @param    self    The class instance that this method operates on.
    # @param    url     URL that the data was retrieved from.
    # @param    data    The data that retrieved from the URL.
    def cache_page_data(self, url, data):
        # Making sure this is a valid page
        if self.path_id is not None:
            # First removing any previous cached data if it exists.
            DatabaseConnector.execute_non_query(
                """
                DELETE FROM page_cache
                WHERE path_id = %s
                """,
                self.path_id
            )

            # Inserting data into cache
            DatabaseConnector.execute_non_query(
                """
                INSERT INTO page_cache(
                    path_id,
                    page_data
                ) VALUES(
                    %s,
                    %s
                )
                """,
                self.path_id,
                CompressionHelper.compress_data(data)
            )

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
        url = self.crawler_executor.parse_url2(url, self.current_url)
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
        url = self.crawler_executor.parse_url(url, self.current_url)
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