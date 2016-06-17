from concurrent.futures import ProcessPoolExecutor
from math import ceil
from NetScanner.NetScanner import NetScanner

class NetScannerExecutor(ProcessPoolExecutor):
    """A child class of ProcessPoolExecutor which executes a specified number of NetScanners"""

    def __init__(self, start_ip, end_ip, max_workers = None):
        self.start_ip = start_ip
        self.end_ip = end_ip
        self.num_ips_per_worker = ceil((self.end_ip - self.start_ip) / max_workers)
        return super().__init__(max_workers)

    def execute_tasks(self):
        print("Commencing scan...")
        print("Start IP: {}\nEnd IP: {}".format(self.start_ip, self.end_ip))
        print("NetScanners: {}".format(self._max_workers))
        next_start_ip = self.start_ip
        for i in range(self._max_workers):
            scanner = NetScanner(i)
            self.submit(scanner.scan_range, next_start_ip, (next_start_ip + self.num_ips_per_worker))
            next_start_ip = next_start_ip + self.num_ips_per_worker
        self.shutdown(wait = True)



