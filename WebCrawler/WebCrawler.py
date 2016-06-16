from os import path
from threading import Thread, Condition
from urllib.parse import urlparse
from WebCrawler.Parser import Parser
import urllib.request
import re
import DebugTools


##
# @class    WebCrawler
#
# @brief    Entity used to crawl through urls and parse them to find and save data.
#
# @author   Edward Callahan
# @date 6/12/2016
class WebCrawler(Parser, Thread):

    ##
    # @fn   __init__(self, swarmController, runCondition, id, downloadImages)
    #
    # @brief    Class initializer.
    #
    # @author   Edward Callahan
    # @date 6/13/2016
    #
    # @param    self            The class instance that this method operates on.
    # @param    swarmController The swarm controller controlling this object.
    # @param    runCondition    The condition that we will wait on when trying to retrieve data.
    # @param    id              The identifier.
    # @param    downloadImages  The download images.
    def __init__(self, swarmController, runCondition, id, downloadImages = False):
        Parser.__init__(self)
        Thread.__init__(self)
        self.swarmController = swarmController
        self.runCondition = runCondition
        self.id = id
        self.downloadImages = downloadImages
        self.waited = False

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

        # Waiting for initial instruction
        self.runCondition.acquire()
        self.runCondition.wait()
        self.runCondition.release()

        while(True):

            self.currentUrl = self.swarmController.getUrlToCrawl()
            if self.currentUrl == False:
                self.swarmController.notifyCrawlerWaiting()
                if self.swarmController.getShouldReturn():
                    return
                self.waited = True
                self.runCondition.acquire()
                self.runCondition.wait()
                self.runCondition.release()
                self.swarmController.notifyCrawlerNoLongerWaiting()
                continue

            if self.currentUrl is None:
                return # Notified to exit thread

            DebugTools.log("[WC:"+ str(self.id) + "] Crawling url: " + self.currentUrl)
            try:
                response = urllib.request.urlopen(self.currentUrl, timeout=5)
                html = response.read().decode("utf-8")
                self.swarmController.cachePageData(self.currentUrl, html)
                self.feed(html)
                self.close()
            except Exception as ex:
                DebugTools.log("[WC:"+ str(self.id) + "] Could not grab url: " + self.currentUrl)
                DebugTools.logException(ex)

    ##
    # @fn   foundUrl(self, url)
    #
    # @brief    Override from Parser
    #
    # @author   Edward Callahan
    # @date 6/12/2016
    #
    # @param    self    The class instance that this method operates on.
    # @param    url     URL that was located.
    def foundUrl(self, url):
        url = self.swarmController.parseUrl(url, self.currentUrl)
        #DebugTools.log("[WC:" + str(self.id) + "] " + url)
        self.swarmController.addUrl(url)

    ##
    # @fn   foundImage(self, url)
    #
    # @brief    Found image url.
    #
    # @author   Edward Callahan
    # @date 6/12/2016
    #
    # @param    self    The class instance that this method operates on.
    # @param    url     The image.
    def foundImage(self, url):
        if not self.downloadImages:
            return
        url = self.swarmController.parseUrl(url, self.currentUrl)
        if self.swarmController.validateUrl(url):
            if self.swarmController.hasImageBeenDownloaded(url):
                return
            DebugTools.log("[WC:"+ str(self.id) + "] Downloading image from: " + url)
            try:
                self.swarmController.addDownloadedImage(url)
                urllib.request.urlretrieve(url, "F:\\Downloaded Images\\" + urllib.parse.quote_plus(url.split("/")[-1]))
            except Exception as ex:
                DebugTools.log("[WC:"+ str(self.id) + "] Failed to download image: " + str(ex))

        