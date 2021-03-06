﻿import sys
import argparse
import searchengine.debugtools
import searchengine.netscanner
import searchengine.solr_tools
from searchengine.webcrawler import CrawlerExecutor
from searchengine.indexer import IndexerExecutor, Indexer
from searchengine.vulnerability_scanner.exploit import ExploitManager
from searchengine.manager.managers import ServerManager

def main(argv):
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-wm', '--webcrawlermanager', action='store_true', help='start the webcrawler networked manager')
    group.add_argument('-w', '--webcrawler', action='store_true', help='enable the webcrawler')
    group.add_argument('-i', '--indexer', action='store_true', help='enable the indexer')
    group.add_argument('-s', '--scanner', type=str, choices=['ptr', 'axfr'], help='enable a particular netscanner')
    group.add_argument('-e', '--exploit', action='store_true', help='enable the exploitation module')
    group.add_argument('-o', '--optimizer', action='store_true', help='start the solr optimizer')
    group.add_argument('-rb', '--rebooster', action='store_true', help='start the rebooster for boosting important results')
    group.add_argument('-dm', '--deltamerge', action='store_true', help='start the delta merge tool (migrates new data from working core to live core)')
    parser.add_argument('-p', '--processes', type=int, default='10', help='the number of processes to use')
    parser.add_argument('--host', type=str, default='', help='the host to connect or bind to for IPC via Manager')
    parser.add_argument('--port', type=int, default=4643, help='the port to connect or bind to for IPC via Manager')
    parser.add_argument('-k', '--authkey', type=str, default='a', help='process authentication key used for IPC via Manager')

    args = parser.parse_args()

    if args.webcrawlermanager:
        manager = ServerManager(args.host, args.port, args.authkey.encode('utf-8') if args.authkey is not None else None)
        input("Press enter key to exit.")
    elif args.webcrawler:
        searchengine.debugtools.log("Starting CrawlerExecutor...")
        c_executor = searchengine.webcrawler.crawler.CrawlerExecutor(
            crawler_type = searchengine.webcrawler.crawler.WebCrawler, 
            max_workers = args.processes,
            ip_address = args.host,
            port = args.port,
            authkey = args.authkey.encode('utf-8') if args.authkey is not None else None
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
    elif args.optimizer:
        searchengine.debugtools.log("Starting optimizer...")
        searchengine.solr_tools.run_optimizer()
    elif args.rebooster:
        searchengine.debugtools.log("Starting rebooster...")
        searchengine.solr_tools.run_rebooster()
    elif args.deltamerge:
        searchengine.debugtools.log("Starting deltamerge...")
        searchengine.solr_tools.run_delta_merge()

if __name__ == "__main__":
    main(sys.argv[1:])

