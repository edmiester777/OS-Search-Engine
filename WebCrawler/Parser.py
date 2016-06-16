from html.parser import HTMLParser, HTMLParseError

##
# @class    Parser
#
# @brief    A parser.
#
# @author   Edward Callahan
# @date 6/12/2016
class Parser(HTMLParser):

    def __init__(self):
        HTMLParser.__init__(self)
        self.tagQueue = []

    ##
    # @fn   handle_starttag(self, tag, attrs)
    #
    # @brief    Executed when we encounter an opening tag.
    #
    # @author   Edward Callahan
    # @date 6/12/2016
    #
    # @param    self    The class instance that this method operates on.
    # @param    tag     The found tag.
    # @param    attrs   The attributes of that tag.
    def handle_starttag(self, tag, attrs):
        # Checking to see if the tag has potential for a url.
        if tag == "a":
            for attr in attrs:
                if attr[0] == "href":
                    self.foundUrl(attr[1])
        # Checking for images.
        elif tag == "img":
            for attr in attrs:
                if attr[0] == "src":
                    self.foundImage(attr[1])

    ##
    # @fn   handle_endtag(self, tag)
    #
    # @brief    Executed when we encounter an ending tag.
    #
    # @author   Edward Callahan
    # @date 6/12/2016
    #
    # @param    self    The class instance that this method operates on.
    # @param    tag     The ended tag.
    def handle_endtag(self, tag):
        pass

    ##
    # @fn   handle_data(self, data)
    #
    # @brief    Executed when we encounter data from inside of a tag.
    #
    # @author   Edward Callahan
    # @date 6/12/2016
    #
    # @param    self    The class instance that this method operates on.
    # @param    data    The data.
    def handle_data(self, data):
        pass


    # ======================================================
    # Abstract Functions
    # ======================================================


    ##
    # @fn   foundUrl(self, url)
    #
    # @brief    Executed any time we locate a URL.
    #
    # @author   Edward Callahan
    # @date 6/12/2016
    #
    # @param    self    The class instance that this method operates on.
    # @param    url     URL that was found.
    def foundUrl(self, url):
        pass


    ##
    # @fn   foundData(self, data)
    #
    # @brief    Executed any time we locate data from inside tags.
    #
    # @author   Edward Callahan
    # @date 6/12/2016
    #
    # @param    self    The class instance that this method operates on.
    # @param    data    The data.
    def foundData(self, data):
        pass

    ##
    # @fn   foundImage(self, data)
    #
    # @brief    Executed when we find an image.
    #
    # @author   Edward Callahan
    # @date 6/12/2016
    #
    # @param    self    The class instance that this method operates on.
    # @param    data    The data.
    def foundImage(self, url):
        pass
