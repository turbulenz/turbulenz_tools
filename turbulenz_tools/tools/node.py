# Copyright (c) 2009-2011,2013 Turbulenz Limited
"""
Utility for manipluating Nodes.
"""

__version__ = '1.0.0'

class NodeName(object):
    """Node class to consistent name ."""

    def __init__(self, name):
        self.name = name
        self.path = [ ]

    def add_parent(self, parent):
        """Add the name for a parent node."""
        self.path.append(parent)

    def add_parents(self, parents):
        """Add a list of names for the parent nodes."""
        self.path.extend(parents)

    def add_parent_node(self, parent_node):
        """Add a parent node as a parent."""
        self.add_parents(parent_node.hierarchy_names())
        return self

    def add_path(self, path):
        """Add a path for the parent nodes which is split by '/'."""
        self.path = path.split('/')

    def leaf_name(self):
        """Return the leaf node name."""
        return self.name

    def hierarchy_names(self):
        """Return a list of all the node names."""
        return self.path + [self.name]

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        if len(self.path) > 0:
            return '/'.join(self.path) + '/' + self.name
        else:
            return self.name
