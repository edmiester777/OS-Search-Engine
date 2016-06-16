import socket
from ipaddress import IPv4Address

class NetScanner:
    """This class scans a given range of IPv4 addresses for PTR records and probes specified services."""

    def __init__(self, scannerId, probeServices = True):
        self.scannerId = scannerId
        self.probeServices = probeServices

    def scanRange(self, startIp, endIp):
        for i in range(startIp, endIp):
            try:
                print("[SCNR #{:02}] ".format(self.scannerId), end="")
                ipv4Address = IPv4Address(i).exploded
                hostnameInfo = socket.getnameinfo((ipv4Address, 0), socket.NI_NAMEREQD)
                print("PTR record: {}".format(hostnameInfo))
                if self.probeServices:
                    self.probeService(ipv4Address, 'http')
            except socket.error as e:
                # error handling at its finest...
                print(e.args)
                pass    

    def probeService(self, ip, service):
        pass

    def insertRecordIntoDb(hostname, ip):
        pass