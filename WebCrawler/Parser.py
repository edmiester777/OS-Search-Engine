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
                    self.found_url(attr[1])
        # Checking for images.
        elif tag == "img":
            for attr in attrs:
                if attr[0] == "src":
                    self.found_image(attr[1])

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
    # @fn   found_url(self, url)
    #
    # @brief    Executed any time we locate a URL.
    #
    # @author   Edward Callahan
    # @date 6/12/2016
    #
    # @param    self    The class instance that this method operates on.
    # @param    url     URL that was found.
    def found_url(self, url):
        pass

    ##
    # @fn   found_data(self, data)
    #
    # @brief    Executed any time we locate data from inside tags.
    #
    # @author   Edward Callahan
    # @date 6/12/2016
    #
    # @param    self    The class instance that this method operates on.
    # @param    data    The data.
    def found_data(self, data):
        pass

    ##
    # @fn   found_image(self, url)
    #
    # @brief    Executed when we find an image.
    #
    # @author   Edward Callahan
    # @date 6/12/2016
    #
    # @param    self    The class instance that this method operates on.
    # @param    url     The data.
    def found_image(self, url):
        pass
