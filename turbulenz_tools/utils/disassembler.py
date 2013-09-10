# Copyright (c) 2010-2011,2013 Turbulenz Limited
"""
Python module that handles JSON asset disassembling into HTML.
"""

#######################################################################################################################

def ordered(d):
    keys = d.keys()
    keys.sort()
    for k in keys:
        yield(k, d[k])

# pylint: disable=R0201
class Json2txtRenderer(object):

    def __init__(self):
        pass

    def span(self, string, span_class=None):
        return string

    def key(self, string):
        return string

    def comment(self, string):
        return string

    ###################################

    def expand(self, node_path_string, expand_all=True):
        return '...'

    def collapse(self):
        return ''

    def node_span(self, node_path_string):
        return ''

    def close_span(self):
        return ''

    ###################################

    def expand_link(self, num, is_list, node_path_string, parent):
        """Creates a link span to expand a dictionary or a list."""
        return '%s%s%s%s%s\n%s' % ( self.node_span(node_path_string),
                                    '[ ' if is_list else '{ ',
                                    self.expand(node_path_string, False),
                                    self.comment(' (%i %s)' % (num, parent)),
                                    ' ]' if is_list else ' }',
                                    self.close_span() )

    def string(self, value, link_prefix=None, link=False):
        asset = unicode(value)
        return asset


class Json2txtColourRenderer(Json2txtRenderer):

    def __init__(self):
        Json2txtRenderer.__init__(self)

    def span(self, string, span_class=None):
        return string

    def key(self, string):
        return '\033[31m%s\033[0m' % string

    def comment(self, string):
        return '\033[34m%s\33[0m' % string

    def string(self, value, link_prefix=None, link=False):
        return '\033[32m"%s"\033[0m' % unicode(value)

    def expand(self, node_path_string, expand_all=True):
        return '\033[34m...\033[0m'


class Json2htmlRenderer(Json2txtRenderer):

    def __init__(self):
        Json2txtRenderer.__init__(self)

    def span(self, string, span_class=None):
        if span_class:
            return '<span class="%s">%s</span>' % (span_class, string)
        else:
            return '<span>%s</span>' % string

    def key(self, string):
        return self.span(string)

    def comment(self, string):
        return self.span(string, 'c')

    ###################################

    def expand(self, node_path_string, expand_all=True):
        c = 'expand c all' if expand_all else 'expand c'
        return '<a class="%s">more</a>' % c

    def collapse(self):
        return '<a class="collapse c">less</a>'

    def node_span(self, node_path_string):
        return '<span class="node" id="node=%s">' % node_path_string

    def close_span(self):
        return '</span>'

    ###################################

    def string(self, value, link_prefix=None, link=False):
        asset = unicode(value)
        if link_prefix and (link or '/' in value):
            return '"<a href="%s/%s">%s</a>"' % (link_prefix, asset, asset)
        else:
            return '"%s"' % asset
# pylint: enable=R0201

#######################################################################################################################

class Disassembler(object):
    """Convert JSON to HTML."""

    def __init__(self, renderer, list_cull=3, dict_cull=3, depth=2, link_prefix='',
                 single_line_string_length=200, auto_expand_child_lenght=500, limit_list_length=1000):
        self.renderer = renderer
        self.list_cull = list_cull
        self.dict_cull = dict_cull
        self.depth = depth

        self.single_line_string_length = single_line_string_length
        self.auto_expand_child_lenght = auto_expand_child_lenght
        self.limit_list_length = limit_list_length

        self.link_prefix = link_prefix

        self.current_node_path = [ ]
        self.node_path_string = ''
        self.current_depth = 0

    def _update_node_path_string(self):
        self.node_path_string = ','.join([str(x) for x in self.current_node_path])

    def _push(self, index):
        self.current_node_path.append(index)
        self._update_node_path_string()
        self.current_depth += 1

    def _pop(self):
        self.current_node_path = self.current_node_path[:-1]
        self._update_node_path_string()
        self.current_depth -= 1

    def _has_more_depth(self):
        return self.current_depth <= self.depth

    def _indents(self):
        return ('  ' * len(self.current_node_path), '  ' * (len(self.current_node_path) - 1))

    ###################################################################################################################

    # This function can render the list on multiple lines.
    def mark_up_list_items(self, output, element, start_element, count):
        """Iterate through the list or its slice and mark up its elements."""
        (indent, minor_indent) = self._indents()
        r = self.renderer

        def _expand_link(length, is_list):
            return r.expand_link(length, is_list, self.node_path_string, 'items' if is_list else 'elements')

        sub_list = element[start_element:start_element + count]
        for i, l in enumerate(sub_list):
            if i < (len(sub_list) - 1):
                comma = ','
                line_indent = indent
            else:
                comma = ''
                line_indent = minor_indent

            self._push(i + start_element)
            if isinstance(l, dict):
                if self._has_more_depth():
                    self.mark_up_dict(output, l)
                else:
                    child_output = [ ]
                    self.mark_up_dict(child_output, l)
                    child_len = reduce(lambda a, b: a + len(b), child_output, 0)
                    if child_len < self.auto_expand_child_lenght:
                        output.extend(child_output)
                    else:
                        output.append(_expand_link(len(l), False))
            elif isinstance(l, (list, tuple)):
                if self._has_more_depth():
                    self.mark_up_list(output, l)
                else:
                    child_output = [ ]
                    self.mark_up_list(child_output, l)
                    child_len = reduce(lambda a, b: a + len(b), child_output, 0)
                    if child_len < self.auto_expand_child_lenght:
                        output.extend(child_output)
                    else:
                        output.append(_expand_link(len(l), True))
            elif isinstance(l, (str, unicode)):
                output.append('%s%s\n' % (r.string(l, self.link_prefix), comma))
            elif isinstance(l, bool):
                output.append('%s%s\n' % ('true' if l else 'false', comma))
            elif l is None:
                output.append('null%s\n' % comma)
            else:
                output.append('%s%s\n' % (str(l), comma))
            output.append(line_indent)
            self._pop()

    def mark_up_single_line_list_items(self, output, element, start_element, count):
        # This function can render on a single line the list.
        (indent, _) = self._indents()
        r = self.renderer
        limit_list_length = self.limit_list_length

        current_length = 0
        for i, x in enumerate(element[start_element:start_element + count]):
            if isinstance(x, (str, unicode)):
                o = r.string(x, self.link_prefix)
            elif isinstance(x, bool):
                o = 'true' if x else 'false'
            elif x is None:
                o = 'null'
            else:
                o = str(x)

            output.append(o)
            if i < (count - 1):
                output.append(', ')

            # We count the size of the element and an extra 2 for the comma and space.
            current_length += len(o) + 2
            if current_length > limit_list_length:
                output.append('\n%s' % indent)
                current_length = 0

    def mark_up_list(self, output, element, parent=None, expand=False):
        (indent, _) = self._indents()
        r = self.renderer

        num_values = len(element)
        over_size_limit = num_values > 2 * self.list_cull

        parent = parent or 'items'

        # Test the list to see if we can render it onto a single line.
        # If we find a dict or list we exit and fall back onto rendering each item on a single line.
        total_length = 0
        for x in element:
            if isinstance(x, (dict, list, tuple)):
                break
            elif isinstance(x, (str, unicode)):
                total_length += len(x)
        else:
            # We got to the end of the list without finding any complicated items.
            # If the total length of strings too large also fall back onto multi line rendering.
            if total_length < self.single_line_string_length:
                if not expand and over_size_limit:
                    output.append('%s[' % r.node_span(self.node_path_string))
                    self.mark_up_single_line_list_items(output, element, 0, self.list_cull)
                    output.append(', %s ' % r.expand(self.node_path_string))
                    self.mark_up_single_line_list_items(output, element, num_values - self.list_cull, self.list_cull)
                    output.append(']%s\n%s' % (r.comment(' (%i of %i %s)' % (self.list_cull * 2, num_values, parent)),
                                               r.close_span()))
                else:
                    output.append('%s[' % ((r.collapse() + ' ') if over_size_limit else ''))
                    self.mark_up_single_line_list_items(output, element, 0, num_values)
                    output.append(']\n%s' % (r.close_span() if over_size_limit else ''))

                # Early out as we've followed a special case.
                return

        # If we get this far we render each item on it's own line.
        if not expand and over_size_limit:
            # display start and end of the list
            output.append('%s[\n%s' % (r.node_span(self.node_path_string), indent))
            self.mark_up_list_items(output, element, 0, self.list_cull)
            output.append('%s\n%s' % (r.expand(self.node_path_string), indent))
            self.mark_up_list_items(output, element, num_values - self.list_cull, self.list_cull)
            output.append(']%s\n%s' % (r.comment(' (%i of %i %s)' % (self.list_cull * 2, num_values, parent)),
                                       r.close_span()))
        else:
            output.append('%s[\n%s' % ((r.collapse() + ' ') if over_size_limit else '', indent))
            self.mark_up_list_items(output, element, 0, num_values)
            output.append(']\n')

    def mark_up_element(self, output, k, v, i=0):
        """Mark up the element of a node."""
        (indent, _) = self._indents()
        r = self.renderer

        def _expand_link(is_list):
            return r.expand_link(len(v), is_list, self.node_path_string, k)

        self._push(i)
        output.append('%s%s: ' % (indent, r.key(k)) if k is not None else '')
        if isinstance(v, dict):
            if self._has_more_depth():
                self.mark_up_dict(output, v, k)
            else:
                child_output = [ ]
                self.mark_up_dict(child_output, v, k)
                child_len = reduce(lambda a, b: a + len(b), child_output, 0)
                if child_len < self.auto_expand_child_lenght:
                    output.extend(child_output)
                else:
                    output.append(_expand_link(False))
        elif isinstance(v, (list, tuple)):
            if self._has_more_depth():
                self.mark_up_list(output, v, k)
            else:
                child_output = [ ]
                self.mark_up_list(child_output, v, k)
                child_len = reduce(lambda a, b: a + len(b), child_output, 0)
                if child_len < self.auto_expand_child_lenght:
                    output.extend(child_output)
                else:
                    output.append(_expand_link(True))
        elif isinstance(v, (str, unicode)):
            output.append('%s\n' % r.string(v, self.link_prefix, (k == 'reference')))
        elif isinstance(v, (bool)):
            output.append('true\n' if v is True else 'false\n')
        elif v is None:
            output.append('none\n')
        else:
            output.append('%s\n' % str(v))
        self._pop()

    def mark_up_dict(self, output, element, parent=None, expand=False):
        """Mark up the node element accordingly to its type into HTML and return as a string."""
        (indent, minor_indent) = self._indents()
        r = self.renderer

        num_values = len(element)
        over_size_limit = num_values > self.dict_cull

        parent = parent or 'elements'

        if not expand and over_size_limit:
            output.append('%s{\n' % r.node_span(self.node_path_string))

            for i, (k, v) in enumerate(ordered(element)):
                if i == self.dict_cull:
                    break
                self.mark_up_element(output, k, v, i)

            output.append('%s%s %s\n%s}\n%s' % (indent,
                                               r.expand(self.node_path_string),
                                               r.comment('(%i of %i %s)' % (self.dict_cull, num_values, parent)),
                                               minor_indent,
                                               r.close_span()))

        else:
            output.append('%s{\n' % ((r.collapse() + ' ') if over_size_limit else ''))
            for i, (k, v) in enumerate(ordered(element)):
                self.mark_up_element(output, k, v, i)
            output.append('%s}\n' % minor_indent)

    def find_node(self, output, json_asset, node_list, expand=False):
        """Find the element in the node list from the json_asset, return marked up in HTML."""

        def _values(elements):
            if isinstance(json_asset, dict):
                for k, v in ordered(json_asset):
                    yield (k, v)
            elif isinstance(json_asset, list):
                for v in json_asset:
                    yield (None, v)

        for i, (k, v) in enumerate(_values(json_asset)):
            if i == node_list[0]:
                self._push(i)
                if (len(node_list) == 1):
                    if isinstance(v, dict):
                        self.mark_up_dict(output, v, k, expand)
                    elif isinstance(v, list):
                        self.mark_up_list(output, v, k, expand)
                    else:
                        # Potentially this should handle the other types correct.
                        # Maybe we could refactor this out of the dict or list methods.
                        output.append('%s\n' % str(v))
                else:
                    self.find_node(output, v, node_list[1:], expand)
                self._pop()

    def mark_up_asset(self, json_asset, expand=False, node=None):
        """Mark up element on HTTP Request."""
        if node is None:
            node_list = [0]
        else:
            node_list = [int(x) for x in node.split(',')]

        output = [ ]
        self.find_node(output, json_asset, node_list, expand)
        return ''.join(output)
