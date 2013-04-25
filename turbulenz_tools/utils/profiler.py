# Copyright (c) 2012-2013 Turbulenz Limited
"""
Keep track of the cost of various points in code
"""

import time

############################################################

class ResultNode(object):
    def __init__(self, node_name):
        self.name = node_name
        self.duration = -1
        self.children = []

        self._start = time.time()

    def stop(self):
        self.duration = time.time() - self._start

    def add_child(self, child_result):
        if -1 != self.duration:
            raise Exception("section '%s' already stopped when trying to add "
                            "child '%s'" % (self.name, child_result.name))
        self.children.append(child_result)

############################################################

class ProfilerDummyImpl(object):
    @classmethod
    def __init__(cls):
        return
    @classmethod
    def start(cls, _):
        return
    @classmethod
    def stop(cls, _):
        return
    @classmethod
    def get_root_nodes(cls):
        return []
    @classmethod
    def dump_data(cls):
        return

############################################################

class ProfilerImpl(object):

    def __init__(self):
        self._root = ResultNode('__')
        self._current_node = self._root
        self._current_stack = []

    def start(self, section_name):
        new_child = ResultNode(section_name)
        self._current_node.add_child(new_child)

        self._current_stack.append(self._current_node)
        self._current_node = new_child

    def stop(self, section_name):

        # Unwind stack until we find the section
        while section_name != self._current_node.name:
            if len(self._current_stack) == 0:
                raise Exception("Cannot find section '%s' to stop it" \
                                    % section_name)

            self._current_node = self._current_stack.pop()

        self._current_node.stop()
        self._current_node = self._current_stack.pop()

    def get_root_nodes(self):
        return self._root.children

    def dump_data(self):

        if 0 == len(self._root.children):
            return

        def _dump_node(node, _indent = 2):
            if node.duration == -1:
                duration = "(unterminated)"
            else:
                duration = node.duration
            _indent_string = " "*_indent
            print "%s%-16s - %s%.6f" % (_indent_string, node.name, _indent_string,
                                    duration)
            for c in node.children:
                _dump_node(c, _indent+2)

        print "TimingData: "
        for r in self._root.children:
            _dump_node(r)

############################################################

class Profiler(object):

    _profiler_impl = ProfilerDummyImpl()

    @classmethod
    def enable(cls):
        if not isinstance(cls._profiler_impl, ProfilerDummyImpl):
            raise Exception("Profiler.enable_profiler() called twice")
        cls._profiler_impl = ProfilerImpl()

    @classmethod
    def start(cls, section_name):
        cls._profiler_impl.start(section_name)

    @classmethod
    def stop(cls, section_name):
        cls._profiler_impl.stop(section_name)

    @classmethod
    def get_root_nodes(cls):
        return cls._profiler_impl.get_root_nodes()

    @classmethod
    def dump_data(cls):
        cls._profiler_impl.dump_data()

############################################################

def _profiler_test():

    ##################################################

    p = ProfilerImpl()
    p.start('section1')
    p.stop('section1')
    roots = p.get_root_nodes()
    assert(1 == len(roots))
    x = roots[0]
    assert('section1' == x.name)
    assert(x.duration > 0)
    assert(0 == len(x.children))

    ##################################################

    p = ProfilerImpl()
    p.start('section1')
    p.start('section1.1')
    p.start('section1.1.1')   # unterminated
    p.start('section1.1.2')
    p.stop ('section1.1.2')
    p.stop ('section1.1')
    p.stop ('section1')
    p.start('section2')
    p.start('section2.1')
    p.stop ('section2.1')
    p.start('section2.2')
    p.stop ('section2.2')
    p.start('section2.3')
    p.stop ('section2.3')
    p.start('section2.4')
    p.stop ('section2.4')
    p.start('section2.5')
    p.stop ('section2.5')
    p.start('section2.6')
    p.stop ('section2.6')
    p.stop ('section2')

    roots = p.get_root_nodes()
    assert(2 == len(roots))

    s1 = roots[0]
    assert('section1' == s1.name)
    assert(s1.duration > 0)
    assert(1 == len(s1.children) > 0)

    s11 = s1.children[0]
    assert('section1.1' == s11.name)
    assert(1 == len(s11.children))

    s111 = s11.children[0]
    assert('section1.1.1' == s111.name)
    assert(-1 == s111.duration)
    assert(1 == len(s111.children))

    s112 = s111.children[0]
    assert('section1.1.2' == s112.name)
    assert(0 < s112.duration)
    assert(0 == len(s112.children))

    s2 = roots[1]
    assert('section2' == s2.name)
    assert(0 < s2.duration)
    assert(6 == len(s2.children))

    p.dump_data()

if __name__ == "__main__":
    exit(_profiler_test())
