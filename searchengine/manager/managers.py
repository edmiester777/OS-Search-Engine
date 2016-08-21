import multiprocessing.managers
import os
import threading

##
# @fn   generate_authkey()
#
# @brief    Generates an authkey for a process.
#           https://docs.python.org/3/library/multiprocessing.html#multiprocessing-auth-keys
#
# @author   Intricate
# @date 8/17/2016
#
# @return   The generated authkey.
def generate_authkey():
    return os.urandom(25)

##
# @class    ServerManager
#
# @brief    A child class of SyncManager from multiprocessing.managers.
#           This class is basically a multiprocessing.context.BaseContext.Manager
#           that allows you to specify constructor arguments such as address and authkey.
#
# @author   Intricate
# @date 8/17/2016
class ServerManager(multiprocessing.managers.SyncManager):
    def __init__(self, ip_address, port, authkey):
        super().__init__(address=(ip_address, port), authkey=authkey)
        super().start()


##
# @class    ClientManager
#
# @brief    A child class of SyncManager from multiprocessing.managers.
#           This class is basically a multiprocessing.context.BaseContext.Manager
#           that allows you to specify constructor arguments such as address and authkey.
#
# @author   Intricate
# @date 8/17/2016
class ClientManager(multiprocessing.managers.SyncManager):
    def __init__(self, ip_address, port, authkey = None):
        super().__init__(address=(ip_address, port), authkey=authkey)
        super().connect()


# This is just registering the Lock and its proxy class with the manager
ServerManager.register('Lock', threading.Lock, multiprocessing.managers.AcquirerProxy)
ClientManager.register('Lock', threading.Lock, multiprocessing.managers.AcquirerProxy)