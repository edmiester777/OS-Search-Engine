from WebCrawler.SwarmController import SwarmController
from Indexer.Indexer import Indexer
import DebugTools
from DatabaseLib.DatabaseConnector import DatabaseConnector
import os
import sys

__HERE__ = None

if __name__ == "__main__":
    if __HERE__ is None:
        __HERE__ = os.path.dirname(__file__)

    if len(sys.argv) > 1 and sys.argv[1] == "indexer":
        DebugTools.log("Starting indexer...")
        indexer = Indexer()
        indexer.start()
        indexer.join()
    else:
        DebugTools.log("Starting web crawler swarm...")
        swarm = SwarmController(16)
        swarm.add_url("https://imgur.com/")
        swarm.wait_for_finish()