import zlib

##
# @class    CompressionHelper
#
# @brief    Class that helps with compression throughout search engine.
#
# @author   Edward Callahan
# @date 6/16/2016
class CompressionHelper:
    DATA_COMPRESSION_LEVEL = 9 #< Max compression level.

    ##
    # @fn   compress_data(data)
    #
    # @brief    Compress data for caching.
    #
    # @author   Edward Callahan
    # @date 6/16/2016
    #
    # @param    data    The data to compress.
    def compress_data(data):
        return zlib.compress(data, CompressionHelper.DATA_COMPRESSION_LEVEL)

    ##
    # @fn   decompress_data(orig)
    #
    # @brief    Decompress cached data.
    #
    # @author   Edward Callahan
    # @date 6/16/2016
    #
    # @param    orig    The compressed data.
    def decompress_data(orig):
        return zlib.decompress(orig)