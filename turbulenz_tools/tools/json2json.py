#!/usr/bin/python
# Copyright (c) 2009-2013 Turbulenz Limited
"""
Operate on Turbulenz JSON assets.
"""
from optparse import OptionParser, TitledHelpFormatter

import logging
LOG = logging.getLogger('asset')

# pylint: disable=W0403
from stdtool import simple_options
from turbulenz_tools.utils.json_utils import float_to_string, log_metrics, merge_dictionaries
# pylint: enable=W0403

from simplejson import load as json_load, dump as json_dump, encoder as json_encoder

__version__ = '1.0.0'
__dependencies__ = [ ]

#######################################################################################################################

def merge(source_files, output_filename="default.json", output_metrics=True):
    """Utility function to merge JSON assets."""
    LOG.info("%i assets -> %s", len(source_files), output_filename)
    merged = { }
    for i, f in enumerate(source_files):
        LOG.info("Processing:%03i:%s", i + 1, f)
        try:
            with open(f, 'r') as source:
                j = json_load(source)
                if isinstance(j, dict):
                    merged = merge_dictionaries(j, merged)
                else:
                    merged = j
        except IOError as e:
            LOG.error("Failed processing: %s", f)
            LOG.error('  >> %s', e)
    try:
        with open(output_filename, 'w') as target:
            LOG.info("Writing:%s", output_filename)
            json_encoder.FLOAT_REPR = float_to_string
            json_dump(merged, target, sort_keys=True, separators=(',', ':'))
    except IOError as e:
        LOG.error('Failed processing: %s', output_filename)
        LOG.error('  >> %s', e)
    else:
        if output_metrics:
            log_metrics(merged)

def _parser():
    usage = "usage: %prog [options] source.json [ ... ] target.json"
    description = 'Merge JSON asset files'

    parser = OptionParser(description=description, usage=usage, formatter=TitledHelpFormatter())
    parser.add_option("--version", action="store_true", dest="output_version", default=False,
                      help="output version number")
    parser.add_option("-v", "--verbose", action="store_true", dest="verbose", default=False, help="verbose output")
    parser.add_option("-s", "--silent", action="store_true", dest="silent", default=False, help="silent running")
    parser.add_option("-m", "--metrics", action="store_true", dest="metrics", default=False,
                      help="output asset metrics")

    return parser

def main():
    (options, args, parser_) = simple_options(_parser, __version__, __dependencies__)

    merge(args[:-1], args[-1], options.metrics)

    return 0

if __name__ == "__main__":
    main()
