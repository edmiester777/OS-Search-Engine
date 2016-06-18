import http.client
import socket
from concurrent.futures import ProcessPoolExecutor
from ipaddress import IPv4Address
from math import ceil
from searchengine.database.connector import DatabaseConnector

class ScannerExecutor(ProcessPoolExecutor):
    """A child class of ProcessPoolExecutor which executes a specified number of Scanners"""

    def __init__(self, start_ip, end_ip, scanner = None, max_workers = None):
        self.start_ip = start_ip
        self.end_ip = end_ip
        self.num_ips_per_worker = ceil((self.end_ip - self.start_ip) / max_workers)
        self.scanner = scanner
        return super().__init__(max_workers)

    def execute_tasks(self):
        print("Commencing scan...")
        print("Start IP: {}\nEnd IP: {}".format(self.start_ip, self.end_ip))
        print("NetScanners: {}".format(self._max_workers))
        next_start_ip = self.start_ip
        for i in range(self._max_workers):
            s = self.scanner(i)
            self.submit(s.scan_range, next_start_ip, (next_start_ip + self.num_ips_per_worker))
            next_start_ip = next_start_ip + self.num_ips_per_worker
        self.shutdown(wait = True)

class PtrScanner:
    """This class scans a given range of IPv4 addresses for PTR records and probes the HTTP service."""

    def __init__(self, scanner_id):
        self.scanner_id = scanner_id

    def scan_range(self, startIp, endIp):
        for i in range(startIp, endIp):
            try:
                print("[SCNR #{:02}] PTR record: ".format(self.scanner_id), end="")
                ipv4_address = IPv4Address(i).exploded
                hostname_info = socket.getnameinfo((ipv4_address, 0), socket.NI_NAMEREQD)
                print(hostname_info[0])
                self.probe_http(hostname_info[0])
            except socket.error as e:
                # error handling at its finest...
                print("not found ({})".format(ipv4_address))

    def probe_http(self, hostname):
        try:
            print("[SCNR #{:02}] HTTP Status: ".format(self.scanner_id), end="")
            connection = http.client.HTTPConnection(hostname, port = None, timeout = 5)
            connection.request("GET", "/")
            response = connection.getresponse()
            print(response.status)
            if self.retrieve_domain_id_from_db(hostname) is None:
                self.insert_host_into_db(0, hostname)
        except Exception as e:
            print(e.args)

    def insert_host_into_db(self, is_https, hostname):
        DatabaseConnector.execute_non_query(
            """
            INSERT INTO domains (is_https, domain_name)
            VALUES (%s, %s)
            """,
            is_https,
            hostname)

    def retrieve_domain_id_from_db(self, hostname):
        # hostname should already be a FQDN at this point
        query_result = DatabaseConnector.execute_query(
            """
            SELECT domain_id
            FROM domains
            WHERE domain_name = %s
            """, 
            hostname)
        return None if (len(query_result) == 0) else query_result[0]["domain_id"]
