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
        self.tagQueue.append(tag)
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
        elif tag == "meta":
            name = None
            content = None
            for attr in attrs:
                if attr[0] == "name":
                    name = attr[1]
                elif attr[0] == "content":
                    content = attr[1]
            if name is not None and content is not None:
                self.found_meta_name_content_pair(name, content)

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
            self.found_title(data)
        
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

    ##
    # @fn   found_title(self, title)
    #
    # @brief    Executed any time we locate a title.
    #
    # @author   Edward Callahan
    # @date 6/20/2016
    #
    # @param    self    The class instance that this method operates on.
    # @param    title   The title.
    def found_title(self, title):
        pass

    ##
    # @fn   found_meta_name_content_pair(self, name, content)
    #
    # @brief    Found a tag that is structured as followed <meta name="{}" content="{}" />
    #
    # @author   Edward Callahan
    # @date 6/21/2016
    #
    # @param    self    The class instance that this method operates on.
    # @param    name    The name.
    # @param    content The content.
    def found_meta_name_content_pair(self, name, content):
        pass
