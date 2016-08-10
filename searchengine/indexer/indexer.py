from searchengine.database.connector import DatabaseConnector
from searchengine.compression.compressionhelper import CompressionHelper
from searchengine.indexer.parser import Parser
from threading import Lock
from concurrent.futures import ThreadPoolExecutor
import searchengine.debugtools
import time
import re

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
    def __init__(self, indexer_type, max_workers):
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
        self.meta_title = ""
        self.meta_description = ""
        self.title = ""
        self.content = ""
        self.running = False
        self.indexer_executor = indexer_executor
        self.id = id
        self.path_id = 0
        self.page_data = None

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
                    self.rank_key_words()

                    # Last minute database work
                    DatabaseConnector.execute_non_query(
                        """
                        DELETE FROM page_details
                        WHERE path_id = %s
                        """,
                        self.path_id
                    )
                    # Checking if there is a new title to insert
                    if len(self.meta_title) > 0 or len(self.title) > 0 or len(self.meta_description) > 0:
                        DatabaseConnector.execute_non_query(
                            """
                            INSERT INTO page_details(
                                path_id,
                                title,
                                description
                            ) VALUES(
                                %s,
                                %s,
                                %s
                            )
                            """,
                            self.path_id,
                            (self.meta_title if len(self.meta_title) > 0 else self.title).strip(),
                            self.meta_description.strip()
                        )

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
    # @fn   rank_key_words(self)
    #
    # @brief    Run algorithm used to rank key words.
    #
    # @author   Edward Callahan
    # @date 6/16/2016
    #
    # @param    self    The class instance that this method operates on.
    def rank_key_words(self):
        content_words = self.split_key_words(self.content)
        title_words = self.split_key_words(self.title)

        # separating unique words and removing unrankable words
        disallowed_words = [
            "and",
            "the",
            "for"
        ]
        unique_words = []
        for word in content_words:
            word = word.lower()
            if len(word) > 2 and len(word) < 35 and word not in disallowed_words and word not in unique_words:
                unique_words.append(word)

        for word in title_words:
            word = word.lower()
            if len(word) > 2 and len(word) < 35 and word not in disallowed_words and word not in unique_words:
                unique_words.append(word)

        # Adding words to database if they are not there
        self.indexer_executor.add_words_if_needed(unique_words)

        # Ranking words (simplified for now)
        #     Algo:
        #     let w = word being ranked
        #     let nT = number of occurrances in title
        #     let nC = number of occurrences in content
        #     let l = length of word
        #     R(w) = 2(nT * l) + (nC * l)
        rank_values = []
        for word in unique_words:
            rank = (2 * len(word) * title_words.count(word)) + (len(word) * content_words.count(word))
            rank_values.append(
                "({}, {}, {})".format(
                    "(SELECT keyword_id FROM keywords WHERE keyword = '{}')".format(word),
                    self.path_id,
                    rank
                )
            )

        # Inserting to database.
        DatabaseConnector.execute_non_query(
            "DELETE FROM keyword_ranking WHERE path_id = %s",
            self.path_id
        )
        DatabaseConnector.execute_non_query(
            """
            INSERT INTO keyword_ranking(
                keyword_id,
                path_id,
                rank
            ) VALUES {}
            """.format(",".join(rank_values))
        )

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