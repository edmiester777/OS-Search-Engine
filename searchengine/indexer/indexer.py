from searchengine.database.connector import DatabaseConnector
from searchengine.compression.compressionhelper import CompressionHelper
from searchengine.indexer.parser import Parser
from threading import Lock
from concurrent.futures import ThreadPoolExecutor
import searchengine.debugtools
import time
import re
import pysolr

SOLR_URL = "http://localhost:8983/solr/search_engine"
SOLR_CORE = "search_engine"

##
# @class    IndexerExecutor
#
# @brief    A child class of ThreadPoolExecutor
#           This class is used to control our multithreading indexer architecture.
#           Handles dispatching tasks to each of our indexers
#           (based on layout of Intricate's CrawlerExecutor)
#
# @author   Edward Callahan
# @date 6/20/2016
class IndexerExecutor(ThreadPoolExecutor):

    ##
    # @fn   __init__(self, indexer_type, max_workers);
    #
    # @brief    Class initializer.
    #
    # @author   Edward Callahan
    # @date 6/20/2016
    #
    # @param    self            The class instance that this method operates on.
    # @param    indexer_type    Type of the indexer.
    # @param    max_workers     The maximum workers.
    #
    # @return   An initialized IndexerExecutor.
    def __init__(self, indexer_type = None, max_workers = None):
        self.mtx = Lock()
        self.indexer_type = indexer_type;
        return super().__init__(max_workers)

    ##
    # @fn   execute_tasks(self)
    #
    # @brief    Executes the tasks operation.
    #
    # @author   Edward Callahan
    # @date 6/20/2016
    #
    # @param    self    The class instance that this method operates on.
    def execute_tasks(self):
        for i in range(self._max_workers):
            indexer = self.indexer_type(self, i)
            self.submit(indexer.run)
        self.shutdown(wait = True)

    ##
    # @fn   add_words_if_needed(self, words)
    #
    # @brief    Adds the words from the list to the database if they have not been added yet.
    #
    # @author   Edward Callahan
    # @date 6/17/2016
    #
    # @param    self    The class instance that this method operates on.
    # @param    words   The words.
    def add_words_if_needed(self, words):
        self.mtx.acquire()
        tbl_values = ["(SELECT '{}' AS keyword)".format(word) for word in words]
        tbl_values_s = " UNION ALL ".join(tbl_values)
        words_not_in = DatabaseConnector.execute_query(
            """
            SELECT words.keyword
            FROM ({}) AS words
            LEFT JOIN keywords USING (keyword)
            WHERE keywords.keyword IS NULL
            """.format(tbl_values_s)
        )
        
        # Building insert values
        values_query = ["('{}')".format(result["keyword"]) for result in words_not_in]

        # Adding to database
        if len(values_query) > 0:
            DatabaseConnector.execute_non_query(
                """
                INSERT INTO keywords(keyword)
                VALUES {}
                """.format(",".join(values_query))
            )
        self.mtx.release()


##
# @class    Indexer
#
# @brief    The task of this unit is to grab the cached data from our database, parse it, 
#           and generate the ranks for them based on key words. Algorithms and task details
#           are outlined below.
#
# @author   Edward Callahan
# @date 6/16/2016
class Indexer(Parser):

    ##
    # @fn   __init__(self)
    #
    # @brief    Class initializer.
    #
    # @author   Edward Callahan
    # @date 6/16/2016
    #
    # @param    self    The class instance that this method operates on.
    def __init__(self, indexer_executor, id):
        Parser.__init__(self)
        global SOLR_URL
        self.solr_instance = pysolr.Solr(SOLR_URL)
        self.meta_title = ""
        self.meta_description = ""
        self.meta_keywords = ""
        self.title = ""
        self.content = ""
        self.running = False
        self.indexer_executor = indexer_executor
        self.id = id
        self.path_id = 0
        self.page_data = None

    ##
    # @fn   __post_to_solr(self);
    #
    # @brief    Posts data and content to solr.
    #
    # @author   Edward Callahan
    # @date 8/12/2016
    #
    # @param    self    The class instance that this method operates on.
    def __post_to_solr(self):
        global SOLR_URL
        global SOLR_CORE
        if len(self.title) == 0 or len(self.content) == 0 or self.path_id is None or self.path_id < 1:
            return
        doc = {
                "id"               : str(self.path_id),
                "path_id"          : self.path_id,
                "meta_keywords"    : self.meta_keywords,
                "meta_description" : self.meta_description,
                "title"            : self.meta_title if len(self.meta_title) > 0 else self.title,
                "content"          : self.content
        }
        self.solr_instance.add([doc])
        self.solr_instance.optimize()
    ##
    # @fn   run(self)
    #
    # @brief    Thread method.
    #
    # @author   Edward Callahan
    # @date 6/16/2016
    #
    # @param    self    The class instance that this method operates on.
    def run(self):
        while True:
            self.get_cached_page()
            if self.path_id == None:
                # We could not get a page to index... waiting then trying again.
                time.sleep(10)
                continue

            else:
                searchengine.debugtools.log("[I:{}] Ranking page with id: {}".format(self.id, str(self.path_id)))
                # We have a page. We now parse it for content.
                try:
                    #decompressed = CompressionHelper.decompress_data(self.page_data).decode("utf-8")
                    self.feed(self.page_data.decode('utf-8'))
                    self.cleanup_string(self.content)
                    self.cleanup_string(self.title)
                    self.content = " ".join(self.split_key_words(self.content))
                    self.__post_to_solr()

                    # Cleanup
                    self.meta_title = ""
                    self.meta_description = ""
                    self.title = ""
                    self.content = ""
                    self.tagQueue.clear()
                except Exception as ex:
                    searchengine.debugtools.log_exception(ex)

    ##
    # @fn   get_cached_page(self)
    #
    # @brief    Gets a page ready to be indexed.
    #
    # @author   Edward Callahan
    # @date 6/16/2016
    #
    # @param    self    The class instance that this method operates on.
    #
    # @return   The cached page.
    def get_cached_page(self):
        self.path_id, self.page_data = DatabaseConnector.call_procedure("GET_CACHED_PAGE", 0, '');

    ##
    # @fn   cleanup_string(self, orig_string)
    #
    # @brief    Cleans the contentent after parse removing extra white space and content that is
    #           evaluated to be unnecessary.
    #
    # @author   Edward Callahan
    # @date 6/17/2016
    #
    # @param    self        The class instance that this method operates on.
    # @param    orig_string The string to clean up.
    def cleanup_string(self, orig_string):
        regex = re.compile(r"[\s|[\\n]+]+") # Removing large groupings of white space as well as "\n" strings in text
        return regex.sub(" ", orig_string)

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