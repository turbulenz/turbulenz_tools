#!/usr/bin/python
# Copyright (c) 2011-2013 Turbulenz Limited
"""
Convert Bitmap Font Generator data (.fnt) files into a Turbulenz JSON asset.
http://www.angelcode.com/products/bmfont/
"""

import re
import sys
import logging

from optparse import OptionParser, OptionGroup, TitledHelpFormatter

# pylint: disable=W0403
from stdtool import standard_output_version, standard_json_out
from asset2json import JsonAsset
# pylint: enable=W0403

__version__ = '2.0.0'
__dependencies__ = ['asset2json']


LOG = logging.getLogger('asset')


#######################################################################################################################

class Bmfont2json(object):
    """Parse a .fnt file and generate a Turbulenz JSON geometry asset."""

    bold_re = re.compile(r'bold=(\d+)')
    italic_re = re.compile(r'italic=(\d+)')
    page_width_re = re.compile(r'scaleW=(\d+)')
    page_height_re = re.compile(r'scaleH=(\d+)')
    line_height_re = re.compile(r'lineHeight=(\d+)')
    base_re = re.compile(r'base=(\d+)')
    num_pages_re = re.compile(r'pages=(\d+)')
    page_re = re.compile(r'page\s+id=(\d+)\s+file="(\S+)"')
    num_chars_re = re.compile(r'chars\s+count=(\d+)')
    num_kernings_re = re.compile(r'kernings\s+count=(\d+)')
    kerning_re = re.compile(r'kerning\s+first=(\d+)\s+second=(\d+)\s+amount=([-+]?\d+)')
    # pylint: disable=C0301
    char_re = re.compile(r'char\s+id=(\d+)\s+x=(\d+)\s+y=(\d+)\s+width=(\d+)\s+height=(\d+)\s+xoffset=([-+]?\d+)\s+yoffset=([-+]?\d+)\s+xadvance=([-+]?\d+)\s+page=(\d+)')
    # pylint: enable=C0301

    def __init__(self, texture_prefix):
        self.bold = 0
        self.italic = 0
        self.glyphs = { }
        self.page_width = 0
        self.page_height = 0
        self.baseline = 0
        self.line_height = 0
        self.num_glyphs = 0
        self.min_glyph_index = 256
        self.texture_pages = []
        self.kernings = { }
        self.texture_prefix = texture_prefix

    def __read_page(self, line):
        found = self.page_re.match(line)
        if not found:
            raise Exception('Page information espected, found: ' + line)

        page_index = int(found.group(1))
        page_file = self.texture_prefix + found.group(2)
        self.texture_pages[page_index] = page_file

        LOG.info("texture page: %s", page_file)

    def __read_char(self, line):
        """Parse one glyph descriptor."""
        found = self.char_re.match(line)
        if not found:
            raise Exception('Char information espected, found: ' + line)

        i = int(found.group(1))
        x = float(found.group(2))
        y = float(found.group(3))
        width = int(found.group(4))
        height = int(found.group(5))
        xoffset = int(found.group(6))
        yoffset = int(found.group(7))
        xadvance = int(found.group(8))
        page = int(found.group(9))

        self.glyphs[i] = {
            'width': width,
            'height': height,
            'awidth': xadvance,
            'xoffset': xoffset,
            'yoffset': yoffset,
            'left': x / self.page_width,
            'top': y / self.page_height,
            'right': (x + width) / self.page_width,
            'bottom': (y + height) / self.page_height,
            'page': page
        }

        if self.min_glyph_index > i:
            self.min_glyph_index = i

    def __read_kerning(self, line):
        """Parse one kerning descriptor."""
        found = self.kerning_re.match(line)
        if not found:
            raise Exception('Kerning information espected, found: ' + line)

        first = int(found.group(1))
        second = int(found.group(2))
        amount = int(found.group(3))

        kerning = self.kernings.get(first, None)
        if kerning is None:
            self.kernings[first] = {second: amount}
        else:
            kerning[second] = amount

#######################################################################################################################

    def parse(self, f):
        """Parse a .fnt file stream."""

        line = f.readline()
        line = line.strip()

        if line.startswith('info '):
            found = self.bold_re.search(line)
            if found:
                self.bold = int(found.group(1))

            found = self.italic_re.search(line)
            if found:
                self.italic = int(found.group(1))

            LOG.info("bold: %d", self.bold)
            LOG.info("italic: %d", self.italic)

            line = f.readline()
            line = line.strip()

        # Common
        if not line.startswith('common '):
            raise Exception('Common information espected, found: ' + line)

        found = self.page_width_re.search(line)
        if not found:
            raise Exception('ScaleW espected, found: ' + line)

        self.page_width = int(found.group(1))

        LOG.info("page width: %d", self.page_width)

        found = self.page_height_re.search(line)
        if not found:
            raise Exception('ScaleH espected, found: ' + line)

        self.page_height = int(found.group(1))

        LOG.info("page height: %d", self.page_height)

        found = self.line_height_re.search(line)
        if not found:
            raise Exception('Line Height espected, found: ' + line)

        self.line_height = int(found.group(1))

        LOG.info("line height: %d", self.line_height)

        found = self.base_re.search(line)
        if not found:
            raise Exception('Base espected, found: ' + line)

        self.baseline = int(found.group(1))

        LOG.info("baseline: %d", self.baseline)

        found = self.num_pages_re.search(line)
        if not found:
            raise Exception('Num pages espected, found: ' + line)

        num_pages = int(found.group(1))
        self.texture_pages = [None] * num_pages

        LOG.info("num texture pages: %d", num_pages)

        # Pages
        line = f.readline()
        line = line.strip()
        while line.startswith('page'):
            self.__read_page(line)
            line = f.readline()
            line = line.strip()

        found = self.num_chars_re.search(line)
        if not found:
            raise Exception('Chars count espected, found: ' + line)

        self.num_glyphs = int(found.group(1))
        if self.num_glyphs <= 0:
            raise Exception('No glyphs found!')

        LOG.info("num glyphs: %d", self.num_glyphs)

        line = f.readline()
        line = line.strip()
        while line.startswith('char'):
            self.__read_char(line)
            line = f.readline()
            line = line.strip()

        # Kernings
        found = self.num_kernings_re.search(line)
        if found:
            num_kernings = int(found.group(1))
            if num_kernings > 0:
                line = f.readline()
                line = line.strip()
                while line.startswith('kerning'):
                    self.__read_kerning(line)
                    line = f.readline()
                    line = line.strip()
        else:
            num_kernings = 0

        LOG.info("num kernings: %d", num_kernings)


    def get_definitions(self, filename):
        """Return a fixed asset object."""
        filename = filename.replace('\\', '/')
        asset = {
            'version': 1,
            'bitmapfontlayouts' : {
                filename: {
                    'pagewidth': self.page_width,
                    'pageheight': self.page_height,
                    'baseline': self.baseline,
                    'lineheight': self.line_height,
                    'numglyphs': self.num_glyphs,
                    'minglyphindex': self.min_glyph_index,
                    'glyphs': self.glyphs,
                    'pages': self.texture_pages
                }
            }
        }
        if self.kernings:
            asset['bitmapfontlayouts'][filename]['kernings'] = self.kernings
        if self.bold:
            asset['bitmapfontlayouts'][filename]['bold'] = True
        if self.italic:
            asset['bitmapfontlayouts'][filename]['italic'] = True
        return asset


#######################################################################################################################

def bmfont2json_parser(description, epilog=None):
    """Standard set of parser options."""
    parser = OptionParser(description=description, epilog=epilog,
                          formatter=TitledHelpFormatter())

    parser.add_option("--version", action="store_true", dest="output_version", default=False,
                      help="output version number")
    parser.add_option("-v", "--verbose", action="store_true", dest="verbose", default=False, help="verbose outout")
    parser.add_option("-s", "--silent", action="store_true", dest="silent", default=False, help="silent running")
    parser.add_option("-m", "--metrics", action="store_true", dest="metrics", default=False,
                      help="output asset metrics")
    parser.add_option("--log", action="store", dest="output_log", default=None, help="write log to file")

    group = OptionGroup(parser, "Asset Generation Options")
    group.add_option("-j", "--json_indent", action="store", dest="json_indent", type="int", default=0, metavar="SIZE",
                     help="json output pretty printing indent size, defaults to 0")
    parser.add_option_group(group)

    group = OptionGroup(parser, "Asset Location Options")
    group.add_option("-p", "--prefix", action="store", dest="texture_prefix", default="textures/", metavar="URL",
                     help="texture URL to prefix to all texture references")
    group.add_option("-a", "--assets", action="store", dest="asset_root", default=".", metavar="PATH",
                     help="PATH of the asset root")
    parser.add_option_group(group)

    group = OptionGroup(parser, "File Options")
    group.add_option("-i", "--input", action="store", dest="input", default=None, metavar="FILE",
                     help="source FILE to process")
    group.add_option("-o", "--output", action="store", dest="output", default="default.json", metavar="FILE",
                     help="output FILE to write to")
    parser.add_option_group(group)

    return parser

def parse(input_filename="default.fontdat", output_filename="default.json", texture_prefix="", asset_root=".",
          options=None):
    """Untility function to convert an .fnt file into a JSON file."""
    with open(input_filename, 'rb') as source:
        asset = Bmfont2json(texture_prefix)
        try:
            asset.parse(source)
            asset_name = input_filename
            if input_filename.startswith(asset_root):
                asset_name = asset_name[(len(asset_root) + 1):-8]
            json_asset = JsonAsset(definitions=asset.get_definitions(asset_name))
            standard_json_out(json_asset, output_filename, options)
            return json_asset
        # pylint: disable=W0703
        except Exception as e:
            LOG.error(str(e))
        # pylint: enable=W0703

def main():
    description = ("Convert Bitmap Font Generator data (.fnt) files into a Turbulenz JSON asset.\n" +
                   "http://www.angelcode.com/products/bmfont/")

    parser = bmfont2json_parser(description)

    (options, args_) = parser.parse_args()

    if options.output_version:
        standard_output_version(__version__, __dependencies__, options.output)
        return

    if options.input is None:
        parser.print_help()
        return

    if options.silent:
        level = logging.CRITICAL
    elif options.verbose or options.metrics:
        level = logging.INFO
    else:
        level = logging.WARNING
    logging.basicConfig(level=level, stream=sys.stdout)

    LOG.info("input: %s", options.input)
    LOG.info("output: %s", options.output)

    if options.texture_prefix != '':
        options.texture_prefix = options.texture_prefix.replace('\\', '/')
        if options.texture_prefix[-1] != '/':
            options.texture_prefix = options.texture_prefix + '/'
        LOG.info("texture URL prefix: %s", options.texture_prefix)

    if options.asset_root != '.':
        LOG.info("root: %s", options.asset_root)

    parse(options.input,
          options.output,
          options.texture_prefix,
          options.asset_root,
          options)

if __name__ == "__main__":
    exit(main())
