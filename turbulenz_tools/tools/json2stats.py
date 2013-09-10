#!/usr/bin/env python
# Copyright (c) 2010-2013 Turbulenz Limited
"""
Report metrics on Turbulenz JSON assets.
"""
import logging

from glob import iglob
from optparse import OptionParser, TitledHelpFormatter

from turbulenz_tools.utils.json_stats import analyse_json
from turbulenz_tools.tools.stdtool import simple_options

__version__ = '1.0.0'
__dependencies__ = ['turbulenz_tools.utils.json_stats']

LOG = logging.getLogger(__name__)

def _parser():
    usage = "usage: %prog [options] asset.json [ ... ]"
    description = """\
Report metrics on JSON asset files.

Metrics are:
"keys": number of bytes used by keys.
"punctuation (punctn)": number of bytes used by JSON punctuation, including '[ ] { } " , :'.
"values": number of bytes used by values. For uncompact JSON files this will also include the white space.
"k%": percentage of total size used by the keys.
"p%": percentage of total size used by the punctuation.
"v%": percentage of total size used by the values (and white space).
"# keys": the total number of keys.
"unique": the number of unique keys.
"total": the total asset size in byte.
"gzip": the asset size after gzip compression.
"ratio": the gzip size as a percentage of the uncompressed total size.
"""
    epilog = 'This tool current assumes the JSON asset is compact with no additional white space.'

    parser = OptionParser(description=description, usage=usage, epilog=epilog, formatter=TitledHelpFormatter())
    parser.add_option("--version", action="store_true", dest="output_version", default=False,
                      help="output version number")
    parser.add_option("-v", "--verbose", action="store_true", dest="verbose", default=False, help="verbose output")
    parser.add_option("-s", "--silent", action="store_true", dest="silent", default=False, help="silent running")
    parser.add_option("-m", "--metrics", action="store_true", dest="metrics", default=False,
                      help="output asset metrics")

    parser.add_option("-H", "--header", action="store_true", dest="header", default=False,
                      help="generate column header")

    return parser

def main():
    (options, args, parser_) = simple_options(_parser, __version__, __dependencies__)

    divider = "+-------------------------+----------------------+---------------+------------------------+"
    if options.header:
        print divider
        print "|    keys: punctn: values |     k%:    p%:    v% | # keys:unique |   total:   gzip: ratio |"
        print divider

    def vadd(a, b):
        return tuple([x + y for (x, y) in zip(a, b)])

    def log((keys, punctuation, values, key_count, unique_count, total_size, compressed_size), f):
        k_percent = keys * 100.0 / total_size
        p_percent = punctuation * 100.0 / total_size
        v_percent = values * 100.0 / total_size
        c_percent = compressed_size * 100.0 / total_size
        print "| %7i:%7i:%7i | %5.1f%%:%5.1f%%:%5.1f%% | %6i:%6i | %7i:%7i:%5.1f%% | %s" % \
            (keys, punctuation, values, k_percent, p_percent, v_percent, key_count, unique_count, \
             total_size, compressed_size, c_percent, f)

    totals = (0, 0, 0, 0, 0, 0, 0)
    for f in args:
        for g in iglob(f):
            stats = analyse_json(g)
            totals = vadd(totals, stats)
            if options.verbose:
                log(stats, g)
    total_string = 'cumulative total and global ratio'
    if options.verbose:
        print divider

    log(totals, total_string)

    if options.header:
        print divider

    return 0

if __name__ == "__main__":
    exit(main())
