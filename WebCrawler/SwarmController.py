from threading import Lock, Condition
from WebCrawler.WebCrawler import WebCrawler
from urllib.parse import urlparse
from os import path
from DatabaseLib.DatabaseConnector import DatabaseConnector
import re
import DebugTools

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
        self.crawledUrls = []
        self.toBeCrawledQueue = []
        self.downloadedImages = []
        self.mutex = Lock()
        self.runConditionMutex = Lock()
        self.runCondition = Condition(self.runConditionMutex)
        self.numWaitingCrawlers = 0
        self.waitConditionMutex = Lock()
        self.waitCondition = Condition(self.waitConditionMutex)

        for i in range(0, numWebCrawlers):
            wc = WebCrawler(self, self.runCondition, i, False)
            self.swarm.append(wc)
            self.swarm[-1].start()

    ##
    # @fn   waitForFinish(self)
    #
    # @brief    Wait for entire swarm to finish.
    #
    # @author   Edward Callahan
    # @date 6/13/2016
    #
    # @param    self    The class instance that this method operates on.
    def waitForFinish(self):
        for crawler in self.swarm:
            crawler.join()

    ##
    # @fn   notifyCrawlerWaiting(self)
    #
    # @brief    Notifies our wait condition that another crawler is in wait state.
    #
    # @author   Edward Callahan
    # @date 6/13/2016
    #
    # @param    self    The class instance that this method operates on.
    def notifyCrawlerWaiting(self):
        self.mutex.acquire()
        self.numWaitingCrawlers += 1
        numWaiting = self.numWaitingCrawlers
        self.mutex.release()
        #DebugTools.log("NumWaiting(" + str(numWaiting) + ") NumToBeCrawled(" + str(len(self.toBeCrawledQueue)) + ") NUmCrawlers(" + str(len(self.swarm)) + ")" + "Eval(" + str(numWaiting >= len(self.swarm)) + ")")
        if numWaiting >= len(self.swarm):
            self.runCondition.acquire()
            self.runCondition.notify_all()
            self.runCondition.release()

    ##
    # @fn   notifyCrawlerNoLongerWaiting(self)
    #
    # @brief    Notifies our wait condition that another crawler is no longer in wait state.
    #
    # @author   Edward Callahan
    # @date 6/13/2016
    #
    # @param    self    The class instance that this method operates on.
    def notifyCrawlerNoLongerWaiting(self):
        self.mutex.acquire()
        self.numWaitingCrawlers -= 1
        self.mutex.release()

    ##
    # @fn   hasImageBeenDownloaded(self, imageUrl)
    #
    # @brief    Check if image has been downloaded.
    #
    # @author   Edward Callahan
    # @date 6/13/2016
    #
    # @param    self        The class instance that this method operates on.
    # @param    imageUrl    URL of the image.
    # @return   True if image has been download, otherwise false
    def hasImageBeenDownloaded(self, imageUrl):
        self.mutex.acquire()
        isIn = imageUrl in self.downloadedImages
        self.mutex.release()
        return isIn

    ##
    # @fn   addUrl(self, url)
    #
    # @brief    Adds a URL to our list to be crawled if it has not been crawled yet.
    #
    # @author   Edward Callahan
    # @date 6/12/2016
    #
    # @param    self    The class instance that this method operates on.
    # @param    url     URL to be added.
    def addUrl(self, url):
        # url validation
        if not self.validateUrl(url):
            return
        # Checking if we already have page
        self.mutex.acquire()
        if self.getPageIdFromUrl(url) is None:
            # Inserting page into database
            parsed = urlparse(url)
            if len(parsed.hostname) == 0:
                return
            host = parsed.hostname
            path = parsed.path
            if len(parsed.query) > 0:
                path += "?" + parsed.query

            # Checking if we need to add domain name to list
            domain_id = self.getDomainIdFromUrl(url)
            if domain_id is None:
                # We need to insert the domain name.
                is_https = 0 if parsed.scheme == "https" else 1
                DatabaseConnector.executeNonQuery(
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
                domain_id = DatabaseConnector.lastInsertId()

            # Inserting path into database
            DatabaseConnector.executeNonQuery(
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
        self.runCondition.acquire()
        self.runCondition.notify()
        self.runCondition.release()

    ##
    # @fn   cachePageData(self, url, data)
    #
    # @brief    Cache data returned from page.
    #
    # @author   Edward Callahan
    # @date 6/15/2016
    #
    # @param    self    The class instance that this method operates on.
    # @param    url     URL that the data was retrieved from.
    # @param    data    The data that retrieved from the URL.
    def cachePageData(self, url, data):
        self.mutex.acquire()

        # Grabbing Page Id
        page_id = self.getPageIdFromUrl(url)

        # Making sure this is a valid page
        if page_id is not None:
            # First removing any previous cached data if it exists.
            DatabaseConnector.executeNonQuery(
                """
                DELETE FROM page_cache
                WHERE path_id = %s
                """,
                page_id
            )

            # Inserting data into cache
            DatabaseConnector.executeNonQuery(
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
                data
            )
        self.mutex.release()

    ##
    # @fn   getUrlToCrawl(self)
    #
    # @brief    Gets URL to crawl.
    #
    # @author   Edward Callahan
    # @date 6/13/2016
    #
    # @param    self    The class instance that this method operates on.
    def getUrlToCrawl(self):
        self.mutex.acquire()

        # Querying database for url to crawl
        response = DatabaseConnector.executeQuery(
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
        if len(response) == 0 and self.numWaitingCrawlers < len(self.swarm):
            # Notifying crawler that we do not currently have urls.
            rel = False
        else:
            # Building url off of database response
            response = response[0]
            rel = "http" + ("s" if int(response["is_https"]) == 1 else "") + "://" + response["domain_name"] + response["path"]

            # Updating database to tell them we updated this data.
            DatabaseConnector.executeNonQuery(
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
    # @fn   getShouldReturn(self)
    #
    # @brief    Used to tell a webcrawler if it should wait (preventind deadlock).
    #
    # @author   Edward Callahan
    # @date 6/13/2016
    #
    # @param    self    The class instance that this method operates on.
    #
    # @returns    True if should return, false if not
    def getShouldReturn(self):
        self.mutex.acquire()
        allow = self.numWaitingCrawlers >= len(self.swarm) and len(self.toBeCrawledQueue) == 0
        self.mutex.release()
        return allow

    ##
    # @fn   addDownloadedImage(self, imageUrl, check = True)
    #
    # @brief    Adds url to a list of downloaded images.
    #
    # @author   Edward callahan
    # @date 6/13/2016
    #
    # @param    self            The class instance that this method operates on.
    # @param    imageUrl        URL of the image.
    # @param    optional check  The optional check for if is in list.
    def addDownloadedImage(self, imageUrl, check = True):
        if check:
            if self.hasImageBeenDownloaded(imageUrl):
                return
        self.mutex.acquire()
        self.downloadedImages.append(imageUrl)
        self.mutex.release()

    ##
    # @fn   validateUrl(self, url)
    #
    # @brief    Validates the URL.
    #
    # @author   Edward Callahan
    # @date 6/12/2016
    #
    # @param    self    The class instance that this method operates on.
    # @param    url     URL to validate.
    # @return   bool    Is url valid
    def validateUrl(self, url):
        url = str(url) #< ensuring url is string
        regex = re.compile("[http|https]+:\/\/[^.]+\.[A-Za-z]+")
        return regex.match(url)

    ##
    # @fn   parseUrl(self, url, currentUrl)
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
    def parseUrl(self, url, currentUrl):
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
    # @fn   getDomainIdFromUrl(self, url)
    #
    # @brief    Gets domain identifier from URL.
    #
    # @author   Edward Callahan
    # @date 6/15/2016
    #
    # @param    self    The class instance that this method operates on.
    # @param    url     URL of the document.
    def getDomainIdFromUrl(self, url):
        parsed = urlparse(url)
        if len(parsed.hostname) == 0:
            return None
        ret = DatabaseConnector.executeQuery(
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
    # @fn   getPageIdFromUrl(self, url)
    #
    # @brief    Gets page identifier from URL.
    #
    # @author   Edward Callahan
    # @date 6/15/2016
    #
    # @param    self    The class instance that this method operates on.
    # @param    url     URL of the document.
    def getPageIdFromUrl(self, url):
        parsed = urlparse(url)
        if len(parsed.hostname) == 0:
            return None
        host = parsed.hostname
        path = parsed.path
        if len(parsed.query) > 0:
            path += "?" + parsed.query
        ret = DatabaseConnector.executeQuery(
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