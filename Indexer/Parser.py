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
    # @date 6/16/2016
    #
    # @param    self    The class instance that this method operates on.
    # @param    tag     The found tag.
    # @param    attrs   The attributes of that tag.
    def handle_starttag(self, tag, attrs):
        self.tagQueue.append(tag)

    ##
    # @fn   handle_endtag(self, tag)
    #
    # @brief    Executed when we encounter an ending tag.
    #
    # @author   Edward Callahan
    # @date 6/16/2016
    #
    # @param    self    The class instance that this method operates on.
    # @param    tag     The ended tag.
    def handle_endtag(self, tag):
        del self.tagQueue[-1]

    ##
    # @fn   handle_data(self, data)
    #
    # @brief    Executed when we encounter data from inside of a tag.
    #
    # @author   Edward Callahan
    # @date 6/16/2016
    #
    # @param    self    The class instance that this method operates on.
    # @param    data    The data.
    def handle_data(self, data):
        if len(self.tagQueue) == 0:
            return # We don't want an empty tag queue

        # Checking if data is compatable, and how to handle it
        if self.tagQueue[-1] == "title":
            pass # Title not implemented
        
        disallowedTags = [
            # Title (disabled because it is used for other purposes in ranking)
            "title",

            # Form tags
            "input",
            "textarea",
            "button",
            "select",
            "optgroup",
            "option",
            "fieldset",
            "output",
            "keygen",
            "datalist",

            # Frame tags
            "frame",
            "frameset",
            "noframes",
            "iframe",

            # Image tags
            "img",
            "map",
            "area",
            "canvas",
            "figcaption",
            "figure",

            # Playable media tags
            "audio",
            "source",
            "track",
            "video",

            # Style and semantic tags
            "style",
            "link",

            # Meta info
            "meta",
            "base",

            # Programming tags
            "script",
            "noscript",
            "applet",
            "embed",
            "object",
            "param"
        ]
        if self.tagQueue[-1] not in disallowedTags:
            self.found_content(data)


    # ======================================================
    # Abstract Functions
    # ======================================================

    ##
    # @fn   found_content(self, content)
    #
    # @brief    Executed any time we locate content from inside tags.
    #
    # @author   Edward Callahan
    # @date 6/12/2016
    #
    # @param    self    The class instance that this method operates on.
    # @param    content The data.
    def found_content(self, content):
        pass
