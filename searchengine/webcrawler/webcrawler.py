from os import path
import os
from threading import Thread, Condition
from urllib.parse import urlparse
from searchengine.webcrawler.parser import Parser
import urllib.request
import re
import searchengine.debugtools


##
# @class    WebCrawler
#
# @brief    Entity used to crawl through urls and parse them to find and save data.
#
# @author   Edward Callahan
# @date 6/12/2016
class WebCrawler(Parser, Thread):

    ##
    # @fn   __init__(self, swarm_controller, run_condition, id, download_images = False)
    #
    # @brief    Class initializer.
    #
    # @author   Edward Callahan
    # @date 6/13/2016
    #
    # @param    self                        The class instance that this method operates on.
    # @param    swarm_controller            The swarm controller controlling this object.
    # @param    run_condition               The condition that we will wait on when trying to
    #                                       retrieve data.
    # @param    id                          The identifier.
    # @param    optional download_images    The download images.
    def __init__(self, swarm_controller, run_condition, id, download_images = False):
        Parser.__init__(self)
        Thread.__init__(self)
        self.swarm_controller = swarm_controller
        self.run_condition = run_condition
        self.id = id
        self.download_images = download_images
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
        self.run_condition.acquire()
        self.run_condition.wait()
        self.run_condition.release()

        while(True):

            self.current_url = self.swarm_controller.get_url_to_crawl()
            if self.current_url == False:
                self.swarm_controller.notify_crawler_waiting()
                self.run_condition.acquire()
                self.run_condition.wait(5)
                self.run_condition.release()
                self.swarm_controller.notify_crawler_no_longer_waiting()
                continue

            if self.current_url is None:
                return # Notified to exit thread

            searchengine.debugtools.log("[WC:"+ str(self.id) + "] Crawling url: " + self.current_url)
            try:
                response = urllib.request.urlopen(self.current_url, timeout=5)
                data = response.read()
                html = data.decode("utf-8")
                self.swarm_controller.cache_page_data(self.current_url, data)
                self.feed(html)
                self.close()
            except Exception as ex:
                searchengine.debugtools.log("[WC:"+ str(self.id) + "] Could not grab url: " + self.current_url)
                searchengine.debugtools.log_exception(ex)

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
        url = self.swarm_controller.parse_url(url, self.current_url)
        #DebugTools.log("[WC:" + str(self.id) + "] " + url)
        self.swarm_controller.add_url(url)

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
        url = self.swarm_controller.parse_url(url, self.current_url)
        if self.swarm_controller.validate_url(url):
            if self.swarm_controller.has_image_been_downloaded(url):
                return
            searchengine.debugtools.log("[WC:"+ str(self.id) + "] Downloading image from: " + url)
            try:
                if not path.isdir(searchengine.debugtools.debug_outfile + "/image_downloads"):
                    os.makedirs(__HERE__ + "/image_downloads")
                self.swarm_controller.add_downloaded_image(url)
                urllib.request.urlretrieve(url,  __HERE__ + "/image_downloads/" + urllib.parse.quote_plus(url.split("/")[-1]))
            except Exception as ex:
                searchengine.debugtools.log("[WC:"+ str(self.id) + "] Failed to download image: " + str(ex))
