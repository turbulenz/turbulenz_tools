# Copyright (c) 2009-2011,2013 Turbulenz Limited
"""
Point map structure similar to a kd-tree but with points on each internal node which allows for fast neighbours lookup.
It takes (N*log N) to build and (N*log N) to query.
"""

# pylint: disable=W0403
import vmath
# pylint: enable=W0403

__version__ = '1.0.0'
__dependencies__ = ['vmath']

#######################################################################################################################

class Node(object):
    """kd-tree node."""

    def __init__(self, vertex_index, split_axis):
        self.vertex_index = vertex_index
        self.split_axis = split_axis
        self.left_child = None
        self.right_child = None

    def points_within_uv_distance(self, positions, position, position_tolerance, uvs, uv, uv_tolerance):
        """Build a list of indexes which are within distance of the point and vertex."""

        def __points_within_distance(node, results):
            """Build a list of indexes which are within distance of the point and vertex."""
            if not node:
                return

            vertex_index = node.vertex_index
            this_position = positions[vertex_index]
            this_uv = uvs[vertex_index]

            if vmath.v3equal(this_position, position, position_tolerance) and vmath.v2equal(this_uv, uv, uv_tolerance):
                results.append(vertex_index)

            split_axis = node.split_axis
            v_axis = this_position[split_axis]
            p_axis = position[split_axis]

            if (p_axis + position_tolerance) < v_axis:
                __points_within_distance(node.left_child, results)
            elif (p_axis - position_tolerance) > v_axis:
                __points_within_distance(node.right_child, results)
            else:
                __points_within_distance(node.left_child, results)
                __points_within_distance(node.right_child, results)

        results = [ ]
        __points_within_distance(self, results)
        return results

    def points_within_distance(self, vertexes, point, distance):
        """Build a list of indexes which are within distance of the point and vertex."""

        def __points_within_distance(node, results):
            """Build a list of indexes which are within distance of the point and vertex."""
            if not node:
                return

            vertex_index = node.vertex_index
            vertex = vertexes[vertex_index]

            if vmath.v3equal(point, vertex, distance):
                results.append(vertex_index)

            split_axis = node.split_axis
            v_axis = vertex[split_axis]
            p_axis = point[split_axis]

            if (p_axis + distance) < v_axis:
                __points_within_distance(node.left_child, results)
            elif (p_axis - distance) > v_axis:
                __points_within_distance(node.right_child, results)
            else:
                __points_within_distance(node.left_child, results)
                __points_within_distance(node.right_child, results)

        results = [ ]
        __points_within_distance(self, results)
        return results

def build_kdtree(vertexes):
    """Build a kd-tree for the vertexes and indexes."""
    return build_kdtree_nodes(vertexes, range(len(vertexes)))

def build_kdtree_nodes(vertexes, indexes, depth=0):
    """Build a kd-tree for the vertexes and indexes."""
    if not indexes:
        return

    # Select axis based on depth so that axis cycles through all valid values
    split_axis = depth % 3

    # Sort point list and choose median as pivot element
    indexes.sort(key=lambda v: vertexes[v][split_axis])
    median = len(indexes) / 2 # choose median

    # Create node and construct subtrees
    node = Node(indexes[median], split_axis)
    node.left_child = build_kdtree_nodes(vertexes, indexes[0:median], depth + 1)
    node.right_child = build_kdtree_nodes(vertexes, indexes[median+1:], depth + 1)

    return node

#######################################################################################################################

if __name__ == "__main__":
    import random
    NUM = 1000
    VERTEXES = [ (random.random(), random.random(), random.random()) for x in range(NUM) ]
    ROOT = build_kdtree(VERTEXES)
    POINT = (0.25, 0.5, 0.75)
    DISTANCE = 0.1
    RESULTS = ROOT.points_within_distance(VERTEXES, POINT, DISTANCE)
    RESULTS.sort()
    for r in RESULTS:
        print "Result: %i %s is close to %s." % (r, VERTEXES[r], POINT)
    print "=" * 80
    for i, x in enumerate(VERTEXES):
        if vmath.v3equal(x, POINT, DISTANCE):
            print "Result: %i %s is close to %s." % (i, x, POINT)
