from concurrent.futures import ProcessPoolExecutor
from NetScanner.NetScanner import NetScanner

class NetScannerExecutor(ProcessPoolExecutor):
    """A child class of ProcessPoolExecutor which executes a specified number of NetScanners"""

    CLASS_A_BEGIN = 0x01000000
    CLASS_A_END = 0x7FFFFFFF
    CLASS_B_BEGIN = 0x80000000
    CLASS_B_END = 0xBFFFFFFF
    CLASS_C_BEGIN = 0xC0000000
    CLASS_C_END = 0xDFFFFFFF

    def __init__(self, max_workers = None):
        return super().__init__(max_workers)

    def execute(self):
        startIp = self.CLASS_A_BEGIN
        endIp = self.CLASS_A_END
        numIpsPerWorker = int((endIp - startIp) / self._max_workers)
        for i in range(self._max_workers):
            scanner = NetScanner(i, probeServices = True)
            self.submit(scanner.scanRange, startIp, (startIp + numIpsPerWorker))
            startIp = startIp + numIpsPerWorker
        self.shutdown(wait = True)



