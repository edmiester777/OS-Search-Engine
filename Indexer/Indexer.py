from DatabaseLib.DatabaseConnector import DatabaseConnector
from CompressionLib.CompressionHelper import CompressionHelper
from Indexer.Parser import Parser
from threading import Thread, Lock
import DebugTools
import time
import re

##
# @class    Indexer
#
# @brief    The task of this unit is to grab the cached data from our database, parse it, 
#           and generate the ranks for them based on key words. Algorithms and task details
#           are outlined below.
#
# @author   Edward Callahan
# @date 6/16/2016
class Indexer(Thread, Parser):

    ##
    # @fn   __init__(self)
    #
    # @brief    Class initializer.
    #
    # @author   Edward Callahan
    # @date 6/16/2016
    #
    # @param    self    The class instance that this method operates on.
    def __init__(self):
        Thread.__init__(self)
        Parser.__init__(self)
        self.current_page = None
        self.content = ""
        self.running = False
        self.mutex = Lock()

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
        self.running = True
        isRunning = True
        while isRunning:
            self.current_page = self.get_cached_page()
            if self.current_page == False:
                # We could not get a page to index... waiting then trying again.
                time.sleep(0.05)
            else:
                DebugTools.log("Ranking page with id: " + str(self.current_page["path_id"]))
                # We have a page. We now parse it for content.
                try:
                    decompressed = CompressionHelper.decompress_data(self.current_page["page_data"]).decode("utf-8")
                    self.feed(decompressed)
                    self.cleanup_content()
                    self.rank_key_words()
                    #Cleanup
                    self.content = ""
                    self.tagQueue.clear()
                except Exception as ex:
                    DebugTools.logException(ex)
            self.mutex.acquire()
            isRunning = self.running
            self.mutex.release()

    ##
    # @fn   cleanup_content(self)
    #
    # @brief    Cleans the contentent after parse removing extra white space and content that is
    #           evaluated to be unnecessary.
    #
    # @author   Edward Callahan
    # @date 6/17/2016
    #
    # @param    self    The class instance that this method operates on.
    def cleanup_content(self):
        regex = re.compile(r"[\s|[\\n]+]+") # Removing large groupings of white space as well as "\n" strings in text
        self.content = regex.sub(" ", self.content)

    ##
    # @fn   get_content_words(self)
    #
    # @brief    Get all valid words from the content string.
    #
    # @author   Edward Callahan
    # @date 6/17/2016
    #
    # @param    self    The class instance that this method operates on.
    def get_content_words(self):
        all_words = re.findall(r"\w+", self.content)

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
        words = self.get_content_words()

        # separating unique words and removing unrankable words
        disallowed_words = [
            "and",
            "the",
            "for"
        ]
        unique_words = []
        for word in words:
            word = word.lower()
            if len(word) > 2 and len(word) < 35 and word not in disallowed_words and word not in unique_words:
                unique_words.append(word)

        # Adding words to database if they are not there
        self.add_words_if_needed(unique_words)

        # counting occurrances of words
        word_count = [words.count(word) for word in unique_words]

        # Ranking words (simplified for now)
        #     Algo:
        #     let w = word being ranked
        #     let n = number of occurrances
        #     let l = length of word
        #     R(w) = n * l
        rank_values = []
        for index in range(0, len(unique_words)):
            rank = len(unique_words[index]) * word_count[index]
            rank_values.append(
                "({}, {}, {})".format(
                    "(SELECT keyword_id FROM keywords WHERE keyword = '{}')".format(unique_words[index]),
                    self.current_page["path_id"],
                    rank
                )
            )

        # Inserting to database.
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
    # @fn   add_words_if_needed(self, words)
    #
    # @brief    Adds the words from the list to the database if they have not
    #           been added yet.
    #
    # @author   Edward Callahan
    # @date 6/17/2016
    #
    # @param    self    The class instance that this method operates on.
    # @param    words   The words.
    def add_words_if_needed(self, words):
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
       

            

    ##
    # @fn   get_cached_page(self)
    #
    # @brief    Gets a page ready to be indexed.
    #
    # @author   Edward Callahan
    # @date 6/16/2016
    #
    # @param    self    The class instance that this method operates on.
    def get_cached_page(self):
        response = DatabaseConnector.execute_query(
            """
            SELECT cache_id,
                   path_id,
                   page_data
            FROM page_cache
            LIMIT 1
            """
        )
        if not response or len(response) == 0:
            return False
        else:
            ret = response[0]
            if ret is not None:
                DatabaseConnector.execute_non_query("DELETE FROM page_cache WHERE cache_id = %s", ret["cache_id"])
                DatabaseConnector.execute_non_query("DELETE FROM keyword_ranking WHERE path_id = %s", ret["path_id"])
            return ret

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