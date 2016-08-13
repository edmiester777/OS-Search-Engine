import sys
import argparse
import searchengine.debugtools
import searchengine.netscanner
from searchengine.webcrawler import CrawlerExecutor
from searchengine.indexer import IndexerExecutor, Indexer
from searchengine.vulnerability_scanner.exploit import ExploitManager

def main(argv):
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-w', '--webcrawler', action='store_true', help='enable the webcrawler')
    group.add_argument('-i', '--indexer', action='store_true', help='enable the indexer')
    group.add_argument('-s', '--scanner', type=str, choices=['ptr', 'axfr'], help='enable a particular netscanner')
    group.add_argument('-e', '--exploit', action='store_true', help='enable the exploitation module')
    parser.add_argument('-p', '--processes', type=int, default='10', help='the number of processes to use')

    args = parser.parse_args()

    if args.webcrawler:
        searchengine.debugtools.log("Starting CrawlerExecutor...")
        c_executor = searchengine.webcrawler.crawler.CrawlerExecutor(
            crawler_type = searchengine.webcrawler.crawler.WebCrawler, 
            max_workers = args.processes
            )
        c_executor.execute_tasks()
    elif args.indexer:
        searchengine.debugtools.log("Starting IndexerExecutor...")
        i_executor = searchengine.indexer.IndexerExecutor(
            indexer_type = searchengine.indexer.Indexer, 
            max_workers = args.processes
            )
        i_executor.execute_tasks()
    elif args.scanner:
        if args.scanner == 'ptr':
            searchengine.debugtools.log("Starting ScannerExecutor...")
            executor = searchengine.netscanner.ScannerExecutor(0x01000400, searchengine.netscanner.constants.CLASS_A_END, scanner = searchengine.netscanner.PtrScanner, max_workers = 15)
            executor.execute_tasks()
        else:
            searchengine.debugtools.log("Scanner option not supported yet.")
    elif args.exploit:
            searchengine.debugtools.log("Starting ExploitManager...")
            exploit_manager = ExploitManager()
            while True:
                exploit_manager.find_domain()

if __name__ == "__main__":
    main(sys.argv[1:])

