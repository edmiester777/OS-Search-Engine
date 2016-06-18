import sys
import getopt
import searchengine.debugtools
import searchengine.netscanner
from searchengine.indexer.indexer import Indexer
from searchengine.webcrawler import CrawlerExecutor


def main(argv):
    try:
        opts, args = getopt.getopt(argv, "hcsi", [])
    except getopt.GetoptError:
        usage()
        #sys.exit(2)
    crawler = False
    scanner = False
    indexer = False
    for opt, arg in opts:
        if opt == '-h':
            usage()
            #sys.exit(2)
        elif opt == '-c':
            crawler = True
        elif opt == '-s':
            scanner = True
        elif opt == '-i':
            indexer = True
    if crawler:
        searchengine.debugtools.log("Starting web crawler swarm...")
        c_executor = searchengine.webcrawler.crawler.CrawlerExecutor(Crawler = searchengine.webcrawler.crawler.WebCrawler, max_workers = 20)
        c_executor.add_url("https://gmail.com")
        c_executor.execute_tasks()
    elif scanner:
        executor = searchengine.netscanner.ScannerExecutor(0x01000400, searchengine.netscanner.constants.CLASS_A_END, scanner = searchengine.netscanner.PtrScanner, max_workers = 15)
        executor.execute_tasks()
    elif indexer:
        searchengine.debugtools.log("Starting indexer...")
        indexer = Indexer()
        indexer.start()
        indexer.join()

def usage():
    print("Usage: driver.py (-c | -s | -i)")

if __name__ == "__main__":
    main(sys.argv[1:])

