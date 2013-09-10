#!/usr/bin/env python
# Copyright (c) 2010-2013 Turbulenz Limited

import logging

from re import sub
from optparse import OptionParser, OptionGroup, TitledHelpFormatter

from turbulenz_tools.utils.xml_json import xml2json
from turbulenz_tools.tools.stdtool import simple_options

__version__ = '1.0.0'
__dependencies__ = ['turbulenz_tools.utils.xml_json']

LOG = logging.getLogger(__name__)

def _parser():
    usage = "usage: %prog [options] -i source.xml -o output.json"
    description = "Convert XML assets into a structured JSON asset."

    parser = OptionParser(description=description, usage=usage, formatter=TitledHelpFormatter())
    parser.add_option("--version", action="store_true", dest="output_version", default=False,
                      help="output version number")
    parser.add_option("-v", "--verbose", action="store_true", dest="verbose", default=False, help="verbose output")
    parser.add_option("-s", "--silent", action="store_true", dest="silent", default=False, help="silent running")
    parser.add_option("-m", "--metrics", action="store_true", dest="metrics", default=False,
                      help="output asset metrics")

    parser.add_option("-i", "--input", action="store", dest="input", help="input XML file to process")
    parser.add_option("-o", "--output", action="store", dest="output", help="output JSON file to process")

    group = OptionGroup(parser, "Asset Generation Options")
    group.add_option("-j", "--json-indent", action="store", dest="json_indent", type="int", default=0, metavar="SIZE",
                     help="json output pretty printing indent size, defaults to 0")
    group.add_option("-n", "--namespace", action="store_true", dest="namespace", default=False,
                     help="maintain XML xmlns namespace in JSON asset keys.")
    group.add_option("-c", "--convert-types", action="store_true", dest="convert_types", default=False,
                     help="attempt to convert values to ints, floats and lists.")

    parser.add_option_group(group)

    return parser

def main():
    (options, args_, parser_) = simple_options(_parser, __version__, __dependencies__)

    try:
        with open(options.input) as xml_file:
            xml_string = xml_file.read()

            # At the moment there doesn't seem to be an obvious way to extract the xmlns from the asset.
            # For now, we'll attempt to just remove it before transforming it into a Python object.

            # <COLLADA xmlns="http://www.collada.org/2005/11/COLLADASchema" version="1.4.1">
            #   ==>
            # <COLLADA version="1.4.1">
            if options.namespace is False:
                xml_string = sub(' xmlns="[^"]*"', '', xml_string)

            json_string = xml2json(xml_string, indent=options.json_indent, convert_types=options.convert_types)
            if options.output:
                with open(options.output, 'w') as target:
                    target.write(json_string)
                    target.write('\n')
            else:
                print json_string

    except IOError as e:
        LOG.error(e)
        return e.errno
    except Exception as e:
        LOG.critical('Unexpected exception: %s', e)
        return 1

if __name__ == "__main__":
    exit(main())
