import dns.query
import dns.resolver
import dns.zone
import socket
import searchengine.solr_tools
import urllib.request
from concurrent.futures import ProcessPoolExecutor
from ipaddress import IPv4Address
from math import ceil
from searchengine.database.connector import DatabaseConnector
from searchengine.debugtools import log, log_exception


##
# @class    ScannerExecutor
#
# @brief    A child class of ProcessPoolExecutor
#           This class will execute a specified number of Scanners.
#
# @author   Intricate
# @date 6/17/2016
class ScannerExecutor(ProcessPoolExecutor):
    """A child class of ProcessPoolExecutor which executes a specified number of Scanners"""

    def __init__(self, start_ip, end_ip, scanner = None, scanner_args = None, max_workers = None):
        self.start_ip = start_ip
        self.end_ip = end_ip
        self.num_ips_per_worker = ceil((self.end_ip - self.start_ip) / max_workers)
        self.scanner = scanner
        return super().__init__(max_workers)

    def execute_tasks(self):
        log("Commencing scan...")
        log("Start IP: {}, End IP: {}".format(self.start_ip, self.end_ip))
        log("NetScanners: {}".format(self._max_workers))
        next_start_ip = self.start_ip
        for i in range(self._max_workers):
            s = self.scanner(i)
            self.submit(s.scan_range, next_start_ip, (next_start_ip + self.num_ips_per_worker))
            next_start_ip = next_start_ip + self.num_ips_per_worker
        self.shutdown(wait = True)


##
# @class    Scanner
#
# @brief    A base Scanner. All Scanners should inherit from this.
#
# @author   Intricate
# @date 6/18/2016
class Scanner:
    def __init__(self, scanner_id):
        self.scanner_id = scanner_id
        self.solr_instance = None

    def run(self, args):
        pass


##
# @class    PtrScanner
#
# @brief    A child class of Scanner
#           This class will scan over a collection of IPv4 addresses
#           in search of DNS PTR records.
#
# @author   Intricate
# @date 6/17/2016
class PtrScanner(Scanner):
    """This class scans a given range of IPv4 addresses for DNS PTR records."""

    def __init__(self, scanner_id):
        return super().__init__(scanner_id)

    def run(self, args):
        if 'start_ip' not in args or 'end_ip' not in args:
            log("[SCNR #{:02}] Either start_ip or end_ip (or both) were not provided to {}".format(self.scanner_id, self.__class__.__name__))
            return
        start_ip = args['start_ip']
        end_ip = args['end_ip']
        self.scan_range(start_ip, end_ip)

    def scan_range(self, start_ip, end_ip):
        if self.solr_instance is None:
            self.solr_instance = searchengine.solr_tools.get_solr_instance('working', url_offset = 0)
        for i in range(start_ip, end_ip):
            try:
                ipv4_address = IPv4Address(i).exploded
                hostname_info = socket.getnameinfo((ipv4_address, 0), socket.NI_NAMEREQD)
                log("[SCNR #{:02}] PTR record: {}".format(self.scanner_id, hostname_info[0]))
                self.__probe_http(hostname_info[0])
            except socket.error as e:
                log_exception(e.args)
                log_exception("not found ({})".format(ipv4_address))

    def __probe_http(self, hostname):
        try:
            request = urllib.request.Request(
                    "http://" + hostname,
                    headers = {
                        "User-Agent" : "OS-SEARCH-ENGINE-CRAWLER"
                    }
                )
            response = urllib.request.urlopen(request, timeout = 5)
            log("[SCNR #{:02}] HTTP Status: {}".format(self.scanner_id, response.status))
            self.__post_host_to_solr(0, hostname)
        except Exception as e:
            log_exception(e.args)

    def __post_host_to_solr(self, is_https, hostname):
        docs = []
        docs.append({
            'id'                : hostname,
            'is_https'          : is_https,
            'last_update_time'  : 0
        })
        self.solr_instance.add(docs, commit = True, overwrite = True)


##
# @class    AxfrScanner
#
# @brief    A child class of Scanner
#           This class will scan over a collection of hosts, query them for their 
#           authoritative name servers (NS record), and attempt to initiate a zone transfer (AXFR)
#
# @author   Intricate
# @date 8/10/2016
class AxfrScanner(Scanner):
    def __init__(self, scanner_id):
        return super().__init__(scanner_id)

    def run(self, args):
        while(True):
            pass

    def check_host(self, hostname):
        # Query the host's authoritative name servers...
        try:
            ns_answer = dns.resolver.query(hostname, 'NS')
        except Exception as e:
            log_exception(e.args)
            return
        for nameserver in ns_answer.rrset:
            if nameserver is None:
                continue
            nameserver = str(nameserver) # < cast NS object to str
            log(nameserver)

            # Attempt a zone transfer
            try:
                axfr_answer = dns.query.xfr(nameserver, hostname)
            except Exception as e:
                log_exception(e.args)
                continue

            try:
                zone = dns.zone.from_xfr(axfr_answer)
            except Exception as e:
                log_exception(e.args)
                continue

            # Zone transfer was successful
            for node in zone.nodes:
                log(node)

    def __get_host_from_solr(self):
        pass


class AScanner(Scanner):
    """This class scans over a collection of hosts for DNS A records."""

    def __init__(self, scanner_id):
        return super().__init__(scanner_id)

