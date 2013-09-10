# Copyright (c) 2010-2011,2013 Turbulenz Limited

import re
import logging

from HTMLParser import HTMLParser

# pylint: disable=W0403
from jsmin import jsmin
# pylint: enable=W0403

LOG = logging.getLogger(__name__)

# pylint: disable=R0904
class HTMLMinifier(HTMLParser):
    """An HTML minifier."""

    REMOVE_WHITESPACE = re.compile(r'\s{2,}').sub

    def __init__(self, output, compact_script=True):
        """output: This callback function will be called when there is data to output.
        A good candidate to use is sys.stdout.write."""
        HTMLParser.__init__(self)
        self.output = output
        self.compact_script = compact_script
        self.pre_count = 0
        self.inside_script = False

    def error(self, message):
        LOG.warning('Warning: %s', message)

    def handle_starttag(self, tag, attributes):
        if 'pre' == tag:
            self.pre_count += 1
        elif 'script' == tag:
            script_type = None
            for (key, value) in attributes:
                if key == 'type':
                    script_type = value
                    break
            if script_type != 'text/html':
                self.inside_script = True
        # This is no longer required as the controller can now signal the middleware to not compact the response.
        #elif 'html' == tag:
        #    # If the request doesn't contain an html tag - we can't assume it isn't inserted within a pre tag (this
        #    # happens in the disassembler.) So we only 'enable' white space removal if we see the html tag.
        #    self.pre_count = 0

        data = self.REMOVE_WHITESPACE(' ', self.get_starttag_text())
        self.output(data)

    def handle_startendtag(self, tag, attributes):
        #self.handle_starttag(tag, attributes)
        #self.handle_endtag(tag)
        data = self.REMOVE_WHITESPACE(' ', self.get_starttag_text())
        self.output(data)

    def handle_endtag(self, tag):
        if 'pre' == tag:
            self.pre_count -= 1
        elif 'script' == tag:
            self.inside_script = False
        self.output('</%s>' % tag)

    def handle_data(self, data):
        if self.inside_script:
            if self.compact_script:
                data = jsmin(data)
        elif self.pre_count == 0:
            data = self.REMOVE_WHITESPACE(' ', data)
            if data == ' ':
                return
        self.output(data)

    def handle_charref(self, name):
        self.output('&#%s;' % name)

    def handle_entityref(self, name):
        self.output('&%s;' % name)

    def handle_comment(self, data):
        return

    def handle_decl(self, data):
        self.output('<!%s>' % data)
        return

    def handle_pi(self, data):
        return
# pylint: enable=R0904
