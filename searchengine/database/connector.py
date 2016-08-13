from mysql.connector import MySQLConnection
from multiprocessing import Lock
import mysql
import searchengine.debugtools

##################################################
# Below is configuration values
##################################################
host = "127.0.0.1"
databaseName = "search_engine"
user = "root"
password = "aaaa"

##
# @class    DatabaseConnector
#
# @brief    A class controlling queries and database connections.
#
# @author   Edward Callahan
# @date 6/15/2016
class DatabaseConnector:
    #__sql_connection = MySQLConnection(host=host, database=databaseName, user = user, password = password)
    __mutex = Lock()

    ##
    # @fn   __init__(self)
    #
    # @brief    Class initializer.
    #
    # @author   Edward Callahan
    # @date 6/15/2016
    #
    # @param    self    The class instance that this method operates on.
    def __init__(self):
        pass

    ##
    # @fn   execute_query(query, *params)
    #
    # @brief    Executes the query operation.
    #
    # @author   Edward Callahan
    # @date 6/15/2016
    #
    # @param    query   The query.
    # @param    params  If non-null, options for controlling the operation.
    def execute_query(query, *params):
        DatabaseConnector.__mutex.acquire()
        cursor = DatabaseConnector.__sql_connection.cursor(dictionary = True)
        ret = None
        try:
            cursor.execute(query, params)
            ret = cursor.fetchall()
        except Exception as ex:
            searchengine.debugtools.log_exception(ex)
            ret = False
        finally:
            cursor.close()
        DatabaseConnector.__mutex.release()
        return ret

    ##
    # @fn   execute_non_query(query, *params)
    #
    # @brief    Executes the query operation.
    #
    # @author   Edward Callahan
    # @date 6/15/2016
    #
    # @param    query   The query.
    # @param    params  If non-null, options for controlling the operation.
    def execute_non_query(query, *params):
        DatabaseConnector.__mutex.acquire()
        cursor = DatabaseConnector.__sql_connection.cursor()
        ret = None
        try:
            cursor.execute(query, params)
            DatabaseConnector.__sql_connection.commit()
            ret = True
        except Exception as ex:
            searchengine.debugtools.log_exception(ex)
            ret = False
        finally:
            cursor.close()
        DatabaseConnector.__mutex.release()
        return ret

    ##
    # @fn   call_procedure(process_name, *args)
    #
    # @brief    Call a stored procedure from database.
    #
    # @author   Edward Callahan
    # @date 8/8/2016
    #
    # @param    process_name    Name of the process.
    # @param    args            Arguments for procedure following the same order as what is stored.
    def call_procedure(process_name, *args):
        DatabaseConnector.__mutex.acquire()
        cursor = DatabaseConnector.__sql_connection.cursor()
        ret = None
        try:
            response = cursor.callproc(process_name, args)
            ret = response
        except Exception as ex:
            searchengine.debugtools.log_exception(ex)
            ret = None
        finally:
            cursor.close()

        DatabaseConnector.__mutex.release()
        return ret

    ##
    # @fn   lastInsertId()
    #
    # @brief    Get the last insert identifier from server.
    #
    # @author   Edward Callahan
    # @date 6/15/2016

    def last_insert_id():
        return DatabaseConnector.execute_query("SELECT LAST_INSERT_ID() AS last_id")[0]["last_id"]

    ##
    # @fn   close(self)
    #
    # @brief    Close the connection to the database.
    #
    # @author   Edward Callahan
    # @date 6/15/2016
    #
    # @param    self    The class instance that this method operates on.
    def close():
        DatabaseConnector.__sql_connection.close()