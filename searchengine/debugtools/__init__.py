import os
import sys
import traceback
from threading import Lock

mutex = Lock()

#########################################
# Debug variables
#########################################

print_stack = False
debug_outfile = os.path.dirname(__file__)

##
# @fn   log(text)
#
# @brief    Log text to screen while protecting encoding errors.
#
# @author   Edward Callahan
# @date 6/12/2016
#
# @param    text    The text.
def log(text):
    global mutex
    pText = str(text.encode("utf-8", errors="replace"))[2:-1]
    mutex.acquire()
    print(pText)
    log_file = open(debug_outfile + "/WebCrawlerOutput.log", "a")
    log_file.writelines(pText + "\n")
    log_file.close()
    mutex.release()

##
# @fn   logException(exception)
#
# @brief    Logs an exception.
#
# @author   Edward callahan
# @date 6/13/2016
#
# @param    exception   The exception.

def log_exception(exception):
    global mutex
    global print_stack
    global __HERE__
    pText = None
    if(print_stack):
        pText = traceback.format_exc()
    else:
        pText = str(exception)
    mutex.acquire()
    print(pText)
    log_file = open(debug_outfile + "/WebCrawlerOutput.log", "a")
    log_file.writelines(pText + "\n")
    log_file.close()
    mutex.release()