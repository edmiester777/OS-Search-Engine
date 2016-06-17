from threading import Lock, Condition
from WebCrawler.WebCrawler import WebCrawler
from urllib.parse import urlparse
from os import path
from DatabaseLib.DatabaseConnector import DatabaseConnector
import re
import DebugTools
from CompressionLib.CompressionHelper import CompressionHelper

##
# @class    SwarmController
#
# @brief    Defines swarm controller class.
#           This class is used to controll our multithreading webcrawler archetecture.
#           Handles dispatching tasks to each of our webcrawlers.
#
# @author   Edward Callahan
# @date 6/13/2016
class SwarmController:

    ##
    # @fn   __init__(self, numWebCrawlers = 16)
    #
    # @brief    Class initializer.
    #
    # @author   Edward Callahan
    # @date 6/13/2016
    #
    # @param    self                    The class instance that this method operates on.
    # @param    optional numWebCrawlers The optional number web crawlers in swarm.
    def __init__(self, numWebCrawlers = 16):
        self.swarm = []
        self.mutex = Lock()
        self.condition_mutex = Lock()
        self.condition = Condition(self.condition_mutex)
        self.num_waiting_crawlers = 0

        for i in range(0, numWebCrawlers):
            wc = WebCrawler(self, self.condition, i, False)
            self.swarm.append(wc)
            self.swarm[-1].start()

    ##
    # @fn   wait_for_finish(self)
    #
    # @brief    Wait for entire swarm to finish.
    #
    # @author   Edward Callahan
    # @date 6/13/2016
    #
    # @param    self    The class instance that this method operates on.
    def wait_for_finish(self):
        for crawler in self.swarm:
            crawler.join()

    ##
    # @fn   notify_crawler_waiting(self)
    #
    # @brief    Notifies our wait condition that another crawler is in wait state.
    #
    # @author   Edward Callahan
    # @date 6/13/2016
    #
    # @param    self    The class instance that this method operates on.
    def notify_crawler_waiting(self):
        self.mutex.acquire()
        self.num_waiting_crawlers += 1
        num_waiting = self.num_waiting_crawlers
        self.mutex.release()
        #DebugTools.log("NumWaiting(" + str(numWaiting) + ") NumToBeCrawled(" + str(len(self.toBeCrawledQueue)) + ") NUmCrawlers(" + str(len(self.swarm)) + ")" + "Eval(" + str(numWaiting >= len(self.swarm)) + ")")
        if num_waiting >= len(self.swarm):
            self.condition.acquire()
            self.condition.notify_all()
            self.condition.release()

    ##
    # @fn   notify_crawler_no_longer_waiting(self)
    #
    # @brief    Notifies our wait condition that another crawler is no longer in wait state.
    #
    # @author   Edward Callahan
    # @date 6/13/2016
    #
    # @param    self    The class instance that this method operates on.
    def notify_crawler_no_longer_waiting(self):
        self.mutex.acquire()
        self.num_waiting_crawlers -= 1
        self.mutex.release()

    ##
    # @fn   has_image_been_downloaded(self, image_url)
    #
    # @brief    Check if image has been downloaded.
    #
    # @author   Edward Callahan
    # @date 6/13/2016
    #
    # @param    self        The class instance that this method operates on.
    # @param    image_url   URL of the image.
    #                       
    # @return    True if image has been download, otherwise false.
    def has_image_been_downloaded(self, image_url):
        self.mutex.acquire()
        is_in = image_url in self.downloadedImages
        self.mutex.release()
        return is_in

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
            allowed = False
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
            for ft in allowed_types:
                if path_split[-1].endswith("." + ft):
                    allowed = True
                    break
            if not allowed:
                return


        # Checking if we already have page
        self.mutex.acquire()
        if self.get_page_id_from_url(url) is None:
            # Inserting page into database
            if len(parsed.hostname) == 0:
                return
            host = parsed.hostname
            path = parsed.path
            if len(parsed.query) > 0:
                path += "?" + parsed.query

            # Checking if we need to add domain name to list
            domain_id = self.get_domain_id_from_url(url)
            if domain_id is None:
                # We need to insert the domain name.
                is_https = 0 if parsed.scheme == "https" else 1
                DatabaseConnector.execute_non_query(
                    """
                    INSERT INTO domains(
                        is_https,
                        domain_name
                    ) VALUES(
                        %s,
                        %s
                    )
                    """,
                    is_https,
                    host
                )
                domain_id = DatabaseConnector.last_insert_id()

            # Inserting path into database
            DatabaseConnector.execute_non_query(
                """
                INSERT INTO paths (
                    domain_id,
                    path,
                    last_update_time
                ) VALUES(
                    %s,
                    %s,
                    0
                )
                """,
                domain_id,
                path
            )
        self.mutex.release()
        self.condition.acquire()
        self.condition.notify()
        self.condition.release()

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
        self.mutex.acquire()

        # Grabbing Page Id
        page_id = self.get_page_id_from_url(url)

        # Making sure this is a valid page
        if page_id is not None:
            # First removing any previous cached data if it exists.
            DatabaseConnector.execute_non_query(
                """
                DELETE FROM page_cache
                WHERE path_id = %s
                """,
                page_id
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
                page_id,
                CompressionHelper.compress_data(data)
            )

            self.mutex.release()

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
        self.mutex.acquire()

        # Querying database for url to crawl
        response = DatabaseConnector.execute_query(
            """
            SELECT domains.is_https AS is_https,
                   domains.domain_name AS domain_name,
                   paths.path AS path,
                   paths.path_id AS path_id
            FROM paths
            JOIN domains ON paths.domain_id = domains.domain_id
            WHERE paths.last_update_time < NOW() - INTERVAL 1 WEEK
            LIMIT 1
            """
        )
        # Checking if we have urls.
        if response != False and len(response) == 0 and self.num_waiting_crawlers < len(self.swarm):
            # Notifying crawler that we do not currently have urls.
            rel = False
        else:
            # Building url off of database response
            response = response[0]
            rel = "http" + ("s" if int(response["is_https"]) == 1 else "") + "://" + response["domain_name"] + response["path"]

            # Updating database to tell them we updated this data.
            DatabaseConnector.execute_non_query(
                """
                UPDATE paths
                SET last_update_time = NOW()
                WHERE path_id = %s
                """,
                response["path_id"]
            )
        self.mutex.release()

        return rel

    ##
    # @fn   add_downloaded_image(self, imageUrl, check = True)
    #
    # @brief    Adds url to a list of downloaded images.
    #
    # @author   Edward callahan
    # @date 6/13/2016
    #
    # @param    self            The class instance that this method operates on.
    # @param    imageUrl        URL of the image.
    # @param    optional check  check  The optional check for if is in list.
    def add_downloaded_image(self, imageUrl, check = True):
        if check:
            if self.has_image_been_downloaded(imageUrl):
                return
        self.mutex.acquire()
        self.downloadedImages.append(imageUrl)
        self.mutex.release()

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
    # @fn   get_page_id_from_url(self, url)
    #
    # @brief    Gets page identifier from URL.
    #
    # @author   Edward Callahan
    # @date 6/15/2016
    #
    # @param    self    The class instance that this method operates on.
    # @param    url     URL of the document.
    def get_page_id_from_url(self, url):
        parsed = urlparse(url)
        if len(parsed.hostname) == 0:
            return None
        host = parsed.hostname
        path = parsed.path
        if len(parsed.query) > 0:
            path += "?" + parsed.query
        ret = DatabaseConnector.execute_query(
            """
            SELECT path_id
            FROM paths
            JOIN domains ON paths.domain_id = domains.domain_id
            WHERE domains.domain_name = %s
            AND paths.path = %s
            """,
            host,
            path
        )
        if len(ret) == 0:
            return None
        return ret[0]["path_id"]