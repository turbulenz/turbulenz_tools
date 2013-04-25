# Copyright (c) 2009-2011,2013 Turbulenz Limited

from os.path import getsize as path_getsize
from zlib import compress as zlib_compress
from simplejson import loads as json_loads

__version__ = '1.0.0'

def analyse_json(filename):
    """Utility to return the ratio of key size, punctuation size, and leaf value size."""

    unique_keys = { }

    def __get_size(j):
        """Recurse to generate size."""
        (keys, punctuation, key_count) = (0, 0, 0)
        if isinstance(j, list):
            punctuation += 1 # [
            punctuation += (len(j) - 1) # ,
            for v in j:
                sub_k, sub_p, sub_count = __get_size(v)
                keys += sub_k
                punctuation += sub_p
                key_count += sub_count
            punctuation += 1 # ]
        elif isinstance(j, dict):
            punctuation += 1 # {
            if len(j.keys()) > 1:
                punctuation += (len(j.keys()) - 1) # ,
            for k, v in j.iteritems():
                if k not in unique_keys:
                    unique_keys[k] = True
                key_count += 1
                punctuation += 1 # "
                keys += len(k)
                punctuation += 1 # "
                punctuation += 1 # :
                sub_k, sub_p, sub_count = __get_size(v)
                keys += sub_k
                punctuation += sub_p
                key_count += sub_count
            punctuation += 1 # }
        elif isinstance(j, (str, unicode)):
            punctuation += 1 # "
            punctuation += 1 # "
        return (keys, punctuation, key_count)

    total_size = path_getsize(filename)
    with open(filename, 'r') as f:
        data = f.read()
        j = json_loads(data)

        (keys, punctuation, key_count) = __get_size(j)
        values = total_size - (keys + punctuation)
        unique_count = len(unique_keys.keys())
        compressed_size = len(zlib_compress(data, 6))

        return (keys, punctuation, values, key_count, unique_count, total_size, compressed_size)
