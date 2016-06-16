from mysql.connector import MySQLConnection
import mysql
import DebugTools

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
    sqlConnection = MySQLConnection(host=host, database=databaseName, user = user, password = password)

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
    # @fn   executeQuery(self, query, *params)
    #
    # @brief    Executes the query operation.
    #
    # @author   Edward Callahan
    # @date 6/15/2016
    #
    # @param    query  The query.
    # @param   params  If non-null, options for controlling the operation.
    def executeQuery(query, *params):
        cursor = DatabaseConnector.sqlConnection.cursor(dictionary = True)
        ret = None
        try:
            cursor.execute(query, params)
            ret = cursor.fetchall()
        except Exception as ex:
            DebugTools.logException(ex)
            ret = False
        finally:
            cursor.close()
        return ret

    ##
    # @fn   executeNonQuery( query, *params)
    #
    # @brief    Executes the query operation.
    #
    # @author   Edward Callahan
    # @date 6/15/2016
    #
    # @param    query   The query.
    # @param    params  If non-null, options for controlling the operation.
    #
    # ### param self    The class instance that this method operates on.

    def executeNonQuery(query, *params):
        cursor = DatabaseConnector.sqlConnection.cursor()
        ret = None
        try:
            cursor.execute(query, params)
            DatabaseConnector.sqlConnection.commit()
            ret = True
        except Exception as ex:
            DebugTools.logException(ex)
            ret = False
        finally:
            cursor.close()
        return ret

    ##
    # @fn   lastInsertId()
    #
    # @brief    Get the last insert identifier from server.
    #
    # @author   Edward Callahan
    # @date 6/15/2016
    def lastInsertId():
        return DatabaseConnector.executeQuery("SELECT LAST_INSERT_ID() AS last_id")[0]["last_id"]

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
        DatabaseConnector.sqlConnection.close()