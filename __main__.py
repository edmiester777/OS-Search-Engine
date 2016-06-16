from WebCrawler.SwarmController import SwarmController
import DebugTools
from DatabaseLib.DatabaseConnector import DatabaseConnector
import os

__HERE__ = None

if __name__ == "__main__":
    if __HERE__ is None:
        __HERE__ = os.path.dirname(__file__)
    DebugTools.log("Starting swarm...")
    swarm = SwarmController(16)
    swarm.addUrl("https://imgur.com/")
    swarm.waitForFinish()