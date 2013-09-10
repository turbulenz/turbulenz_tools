#!/usr/bin/env python
# Copyright (c) 2010-2013 Turbulenz Limited

import logging
import simplejson as json

from optparse import OptionParser, TitledHelpFormatter
from fnmatch import fnmatch

from turbulenz_tools.utils.disassembler import Json2htmlRenderer, Json2txtRenderer, Json2txtColourRenderer, Disassembler
from turbulenz_tools.tools.stdtool import simple_options

__version__ = '1.0.0'
__dependencies__ = ['turbulenz_tools.utils.disassembler']

LOG = logging.getLogger(__name__)

def _parser():
    parser = OptionParser(description='Generate a plain text or html output from a JSON asset. (plain text by default)',
                          usage='%prog -i input.json [-o output.html] [options]',
                          formatter=TitledHelpFormatter())
    parser.add_option("--version", action="store_true", dest="output_version", default=False,
                      help="output version number")
    parser.add_option("-v", "--verbose", action="store_true", dest="verbose", default=False, help="verbose output")
    parser.add_option("-s", "--silent", action="store_true", dest="silent", default=False, help="silent running")

    parser.add_option("-i", "--input", action="store", dest="input", help="input file to process")
    parser.add_option("-o", "--output", action="store", dest="output", help="output file to process")

    parser.add_option("-l", "--listcull", action="store", dest="listcull", type="int", default=3, metavar="NUMBER",
                     help="parameter of the list culling size. 0 - show all (defaults to 3)")
    parser.add_option("-c", "--dictcull", action="store", dest="dictcull", type="int", default=3, metavar="NUMBER",
                     help="parameter of the dictionary culling size. 0 - show all (defaults to 3)")
    parser.add_option("-p", "--path", action="store", dest="path", type="str", default=None,
                     help="path of the required node in the asset tree structure (wildcards allowed)")
    parser.add_option("-d", "--depth", action="store", dest="depth", type="int", default=2, metavar="NUMBER",
                     help="parameter of the dictionary and list rendering depth (defaults to 2).")

    parser.add_option("--html", action="store_true", dest="html", default=False,
                      help="output in html format")
    parser.add_option("--txt", action="store_true", dest="txt", default=False,
                      help="output in plain text format")
    parser.add_option("--color", action="store_true", dest="color", default=False,
                      help="option to turn on the coloured text output")

    return parser

def main():
    (options, args_, parser_) = simple_options(_parser, __version__, __dependencies__)

    source_file = options.input

    LOG.info('%s %s', __file__, source_file)
    LOG.info('input: %s', source_file)

    try:
        with open(source_file, 'r') as source:
            json_asset = json.load(source)

            def find_node(nodes, sub_asset):
                for (k, v) in sub_asset.iteritems():
                    if fnmatch(k, nodes[0]):
                        if len(nodes) == 1:
                            yield (k, sub_asset[k])
                        elif isinstance(v, dict):
                            for n in find_node(nodes[1:], sub_asset[k]):
                                yield n
                            for n in find_node(nodes, sub_asset[k]):
                                yield n

            if options.path:
                node_list = options.path.split('/')

            if options.html:
                renderer = Json2htmlRenderer()
            elif options.color:
                renderer = Json2txtColourRenderer()
            else:
                renderer = Json2txtRenderer()

            disassembler = Disassembler(renderer, options.listcull, options.dictcull, options.depth)
            expand = True

            if options.output:
                with open(options.output, 'w') as target:
                    if options.path:
                        for name, node in find_node(node_list, json_asset):
                            target.write(name + ': ' + disassembler.mark_up_asset({name: node}, expand))
                            target.write('\n')
                    else:
                        target.write(disassembler.mark_up_asset({'root': json_asset}, expand))
                        target.write('\n')
            elif options.color:
                if options.path:
                    for name, node in find_node(node_list, json_asset):
                        print '\033[;31m' + name + '\033[;m' + ': ' + disassembler.mark_up_asset({name: node}, expand),
                else:
                    print disassembler.mark_up_asset({'root': json_asset}, expand)
            else:
                if options.path:
                    for name, node in find_node(node_list, json_asset):
                        print name + ': ' + disassembler.mark_up_asset({name: node}, expand),
                else:
                    print disassembler.mark_up_asset({'root': json_asset}, expand)

    except IOError as e:
        LOG.error(e)
        return e.errno
    except Exception as e:
        LOG.critical('Unexpected exception: %s', e)
        return 1
    return 0

if __name__ == "__main__":
    exit(main())
