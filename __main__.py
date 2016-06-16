from WebCrawler.SwarmController import SwarmController
import DebugTools
from DatabaseLib.DatabaseConnector import DatabaseConnector

DebugTools.log("Starting swarm...")
swarm = SwarmController(16)
swarm.addUrl("https://imgur.com/")
swarm.waitForFinish()