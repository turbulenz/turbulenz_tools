# Copyright (c) 2009-2013 Turbulenz Limited
"""
Mesh class used to hold and process vertex streams.

Supports generating NBTs.
"""

import math
import logging
LOG = logging.getLogger('asset')

# pylint: disable=W0403
import vmath
import pointmap
# pylint: enable=W0403

__version__ = '1.1.0'
__dependencies__ = ['pointmap', 'vmath']

#######################################################################################################################

# cos( 1 pi / 8 ) = 0.923879 ~ cos 22.5 degrees
# cos( 2 pi / 8 ) = 0.707106 ~ cos 45   degrees
# cos( 2 pi / 6 ) = 0.5      ~ cos 60   degress
# cos( 3 pi / 8 ) = 0.382683 ~ cos 67.5 degrees
DEFAULT_POSITION_TOLERANCE = 1e-6
DEFAULT_NORMAL_SMOOTH_TOLERANCE = 0.5 # 0.707106
DEFAULT_TANGENT_SPLIT_TOLERANCE = 0.5 # 0.382683
DEFAULT_ZERO_TOLERANCE = 1e-6
DEFAULT_DONT_NORMALIZE_TOLERANCE = 1e-3
DEFAULT_UV_TOLERANCE = 1e-6
DEFAULT_PLANAR_TOLERANCE = 1e-6
DEFAULT_TANGENT_PROJECTION_TOLERANCE = 1e-10
DEFAULT_COLLINEAR_TOLERANCE = 1e-10
DEFAULT_COPLANAR_TOLERANCE = 1e-16
DEFAULT_PLANAR_HULL_VERTEX_THRESHOLD = 5

def similar_positions(major, positions, pos_tol=DEFAULT_POSITION_TOLERANCE):
    """Iterator to return the index of similar positions."""
    # pos_tol currently unused - using vmath default.
    for i, p in enumerate(positions):
        if vmath.v3equal(major, p):
            yield i

#######################################################################################################################

# pylint: disable=R0902
# pylint: disable=R0904
class Mesh(object):
    """Generate a mesh geometry."""

    class Stream(object):
        """Contains a single stream of vertex attributes."""
        def __init__(self, values, semantic, name, stride, offset):
            """
            ``values`` - array of stream tuples
            ``semantic`` - name of the stream semantic
            ``name`` - human readable name of the stream
            ``stride`` - length of each vertex in the stream
            ``offset`` - offset in the index buffer for this stream
            """
            self.values = values
            self.semantic = semantic
            self.name = name
            self.stride = stride
            self.offset = offset

    def __init__(self, mesh=None):
        # Positions, normals, uvs, skin_indices, skin_weights, primitives
        self.kdtree = None
        if mesh is not None:
            self.positions = mesh.positions[:]
            self.uvs = [ uvs[:] for uvs in mesh.uvs ]
            self.normals = mesh.normals[:]
            self.tangents = mesh.tangents[:]
            self.binormals = mesh.binormals[:]
            self.colors = mesh.colors[:]
            self.skin_indices = mesh.skin_indices[:]
            self.skin_weights = mesh.skin_weights[:]
            self.primitives = mesh.primitives[:]
            self.bbox = mesh.bbox.copy()
        else:
            self.positions = [ ]
            self.uvs = [ [] ]
            self.normals = [ ]
            self.tangents = [ ]
            self.binormals = [ ]
            self.colors = [ ]
            self.skin_indices = [ ]
            self.skin_weights = [ ]
            self.primitives = [ ]
            self.bbox = { }

    ###################################################################################################################

    def set_values(self, values, semantic):
        """Replace the mesh values for a specified semantic."""
        if semantic == 'POSITION':
            self.positions = values
        elif semantic.startswith('TEXCOORD'):
            if semantic == 'TEXCOORD' or semantic == 'TEXCOORD0':
                self.uvs[0] = values
            else:
                index = int(semantic[8:])
                while index >= len(self.uvs):
                    self.uvs.append([])
                self.uvs[index] = values
        elif semantic == 'NORMAL' or semantic == 'NORMAL0':
            self.normals = values
        elif semantic == 'TANGENT':
            self.tangents = values
        elif semantic == 'BINORMAL':
            self.binormals = values
        elif semantic == 'COLOR' or semantic == 'COLOR0':
            self.colors = values
        elif semantic == 'BLENDINDICES':
            self.skin_indices = values
        elif semantic == 'BLENDWEIGHT':
            self.skin_weights = values
        else:
            LOG.warning('Unknown semantic:%s', semantic)

    def get_values(self, semantic):
        """Retrieve the mesh values for a specified semantic."""
        if semantic == 'POSITION':
            values = self.positions
        elif semantic.startswith('TEXCOORD'):
            if semantic == 'TEXCOORD' or semantic == 'TEXCOORD0':
                values = self.uvs[0]
            else:
                index = int(semantic[8:])
                if index >= len(self.uvs):
                    values = []
                else:
                    values = self.uvs[index]
        elif semantic == 'NORMAL' or semantic == 'NORMAL0':
            values = self.normals
        elif semantic == 'TANGENT':
            values = self.tangents
        elif semantic == 'BINORMAL':
            values = self.binormals
        elif semantic == 'COLOR' or semantic == 'COLOR0':
            values = self.colors
        elif semantic == 'BLENDINDICES':
            values = self.skin_indices
        elif semantic == 'BLENDWEIGHT':
            values = self.skin_weights
        else:
            values = None
            LOG.warning('Unknown semantic:%s', semantic)
        return values

    ###################################################################################################################

    def transform(self, transform):
        """Transform the vertexes."""
        self.positions = [ vmath.m43transformp(transform, v) for v in self.positions ]
        self.normals = [ vmath.m43transformn(transform, v) for v in self.normals ]
        self.tangents = [ vmath.m43transformn(transform, v) for v in self.tangents ]
        self.binormals = [ vmath.m43transformn(transform, v) for v in self.binormals ]

    def rotate(self, transform):
        """Rotate the vertexes."""
        self.positions = [ vmath.v3mulm33(v, transform) for v in self.positions ]
        self.normals = [ vmath.v3mulm33(v, transform) for v in self.normals ]
        self.tangents = [ vmath.v3mulm33(v, transform) for v in self.tangents ]
        self.binormals = [ vmath.v3mulm33(v, transform) for v in self.binormals ]

    def invert_v_texture_map(self, uvs=None):
        """Invert the v texture mapping."""
        if not uvs:
            uvs = self.uvs[0]
        if len(uvs) > 0:
            if len(uvs[0]) == 2:
                elements = [ ]
                (_, min_v) = uvs[0]
                (_, max_v) = uvs[0]
                for (_, v) in uvs:
                    min_v = min(v, min_v)
                    max_v = max(v, max_v)
                midV = 2 * ((math.ceil(max_v) + math.floor(min_v)) * 0.5)
                for (u, v) in uvs:
                    elements.append( (u, midV - v) )
                self.uvs[0] = elements
            elif len(uvs[0]) == 3:
                elements = [ ]
                (_, min_v, _) = uvs[0]
                (_, max_v, _) = uvs[0]
                for (_, v, _) in uvs:
                    min_v = min(v, min_v)
                    max_v = max(v, max_v)
                midV = 2 * ((math.ceil(max_v) + math.floor(min_v)) * 0.5)
                for (u, v, w) in uvs:
                    elements.append( (u, midV - v, w) )
                self.uvs[0] = elements

    def generate_vertex_with_new_uv(self, pindex, vindex, new_uv):
        """Create a new vertex for a primitive with a new uv."""
        new_vindex = len(self.positions)                        # Get the new vindex
        while len(self.uvs[0]) < new_vindex:                       # Make sure the UVs and Positions are the same size
            self.uvs[0].append( (0, 0) )
        self.positions.append(self.positions[vindex])           # Clone the position
        self.uvs[0].append(new_uv)                                 # Create a new UV
        (ci1, ci2, ci3) = self.primitives[pindex]               # Update the primitive to use the new vindex
        if (ci1 == vindex):
            self.primitives[pindex] = (new_vindex, ci2, ci3)
        elif (ci2 == vindex):
            self.primitives[pindex] = (ci1, new_vindex, ci3)
        elif (ci3 == vindex):
            self.primitives[pindex] = (ci1, ci2, new_vindex)
        else:
            LOG.error("Didn't find vertex:%i used on primitive:%i", vindex, pindex)

    def generate_primitives(self, indexes):
        """Generate a list of primitives from a list of indexes."""
        # Make triangles out of each sequence of 3 indices.
        self.primitives = zip(indexes[0::3], indexes[1::3], indexes[2::3])

    def generate_bbox(self):
        """Generate a bounding box for the mesh."""
        # Assumes that the positions have at least one element, or the bbox will be nonsensical
        self.bbox['min'] = (float('inf'), float('inf'), float('inf'))
        self.bbox['max'] = (float('-inf'), float('-inf'), float('-inf'))
        for pos in self.positions:
            self.bbox['min'] = vmath.v3min(self.bbox['min'], pos)
            self.bbox['max'] = vmath.v3max(self.bbox['max'], pos)

    def remove_degenerate_primitives(self, remove_zero_length_edges=True,
                                     edge_length_tol=DEFAULT_POSITION_TOLERANCE):
        """Remove degenerate triangles with duplicated indices and optionally
           zero length edges."""
        def _is_degenerate(prim):
            """ Test if a prim is degenerate """
            (i1, i2, i3) = prim
            if i1 == i2 or i1 == i3 or i2 == i3:
                return True
            elif remove_zero_length_edges:
                (v1, v2, v3) = (self.positions[i1], self.positions[i2], self.positions[i3])
                return (vmath.v3is_zero(vmath.v3sub(v2, v1), edge_length_tol) or
                        vmath.v3is_zero(vmath.v3sub(v3, v1), edge_length_tol) or
                        vmath.v3is_zero(vmath.v3sub(v3, v2), edge_length_tol))
            else:
                return False

        self.primitives = [ prim for prim in self.primitives if not _is_degenerate(prim) ]

    ###################################################################################################################

    def generate_smooth_nbts(self):
        """Helper method to generate and smooth the normals, binormals and tangents."""
        if not len(self.normals):
            # Generate the initial normals if there are none.
            self.generate_normals()
        self.generate_tangents()
        self.normalize_tangents()
        self.smooth_tangents()
        self.generate_normals_from_tangents()
        self.smooth_normals()

    def _generate_normal(self, i1, i2, i3, pos_tol):
        """Generate a normal for 3 indexes."""
        (v1, v2, v3) = (self.positions[i1], self.positions[i2], self.positions[i3])
        e1 = vmath.v3sub(v2, v1)
        e2 = vmath.v3sub(v3, v1)
        e_other = vmath.v3sub(v3, v2)
        if (vmath.v3is_zero(e1, pos_tol) or vmath.v3is_zero(e2, pos_tol) or vmath.v3is_zero(e_other, pos_tol)):
            LOG.warning("%s: Found degenerate primitive:%s with edge length < position tolerance[%g]:[%s,%s,%s]",
                        "generate_normals", (i1, i2, i3), pos_tol, e1, e2, e_other)
            return (0, 0, 0)
        return vmath.v3normalize(vmath.v3cross(e1, e2))

    def generate_normals(self, pos_tol=DEFAULT_POSITION_TOLERANCE,
                               dont_norm_tol=DEFAULT_DONT_NORMALIZE_TOLERANCE):
        """Generate a normal per vertex as an average of face normals the primitive is part of."""
        zero = (0, 0, 0)
        self.normals = [zero] * len(self.positions)
        for (i1, i2, i3) in self.primitives:
            n = self._generate_normal(i1, i2, i3, pos_tol)
            self.normals[i1] = vmath.v3add(self.normals[i1], n)
            self.normals[i2] = vmath.v3add(self.normals[i2], n)
            self.normals[i3] = vmath.v3add(self.normals[i3], n)
        for i, n in enumerate(self.normals):
            lsq = vmath.v3lengthsq(n)
            if (lsq > dont_norm_tol): # Ensure normal isn't tiny before normalizing it.
                lr = 1.0 / math.sqrt(lsq)
                self.normals[i] = vmath.v3muls(n, lr)
            else:
                self.normals[i] = zero
                LOG.warning("%s: Found vertex[%i] with normal < normalizable tolerance[%g]:%s",
                            "generate_normals", i, dont_norm_tol, n)

    def smooth_normals(self, include_uv_tol=False,
                             root_node=None,
                             pos_tol=DEFAULT_POSITION_TOLERANCE,
                             nor_smooth_tol=DEFAULT_NORMAL_SMOOTH_TOLERANCE,
                             uv_tol=DEFAULT_UV_TOLERANCE):
        """Smooth normals within a certain position range and normal divergence limit."""

        if not root_node:
            if not self.kdtree:
                # Create a kd-tree to optimize the smoothing performance
                self.kdtree = pointmap.build_kdtree(self.positions)
            root_node = self.kdtree

        uvs = self.uvs[0]
        for i, p in enumerate(self.positions):
            original_normal = self.normals[i]
            accumulate_normal = (0, 0, 0)
            accumulated_indexes = [ ]

            # Generate a list of indexes for the positions close to the evaluation vertex.
            if include_uv_tol:
                uv = uvs[i]
                similiar_positions_indexes = root_node.points_within_uv_distance(self.positions, p, pos_tol,
                                                                                 uvs, uv, uv_tol)
            else:
                similiar_positions_indexes = root_node.points_within_distance(self.positions, p, pos_tol)

            for i in similiar_positions_indexes:
                this_normal = self.normals[i]
                if vmath.v3is_similar(this_normal, original_normal, nor_smooth_tol):
                    accumulate_normal = vmath.v3add(accumulate_normal, this_normal)
                    accumulated_indexes.append(i)
            smooth_normal = vmath.v3unitcube_clamp(vmath.v3normalize(accumulate_normal))
            for i in accumulated_indexes:
                self.normals[i] = smooth_normal

    ###################################################################################################################

    def _clone_vertex_with_new_tangents(self, prim_index, vertex_index, tangent, binormal):
        """Create a new vertex clone all attributes. Then set the new tangent and binormal."""
        clone_index = len(self.positions)
        self.positions.append(self.positions[vertex_index])
        self.normals.append(self.normals[vertex_index])
        for uvs in self.uvs:
            if len(uvs) > vertex_index:
                uvs.append(uvs[vertex_index])
        self.tangents.append(tangent)
        self.binormals.append(binormal)
        if len(self.colors) > vertex_index:
            self.colors.append(self.colors[vertex_index])
        if len(self.skin_indices) > vertex_index:
            self.skin_indices.append(self.skin_indices[vertex_index])
        if len(self.skin_weights) > vertex_index:
            self.skin_weights.append(self.skin_weights[vertex_index])
        return clone_index

    def _split_vertex_with_new_tangents(self, vertex_index, prim_index, split_map, tangent, binormal, tan_split_tol_sq):
        """Split the vertex if the tangents are outside of the accumulation tolerance."""

        def update_primitive_vertexes(primitives, prim_index, source_index, target_index):
            """Update the primitive for a cloned set of vertexes."""
            (p1, p2, p3) = primitives[prim_index]
            if p1 == source_index:
                p1 = target_index
            if p2 == source_index:
                p2 = target_index
            if p3 == source_index:
                p3 = target_index
            primitives[prim_index] = (p1, p2, p3)

        def tangents_within_tolerance(t1, b1, t2, b2, tan_split_tol_sq):
            """Test if the tangents and binormals are within tolerance."""
            tangent_within_tolerance = vmath.v3is_within_tolerance(t1, t2, tan_split_tol_sq)
            binormal_within_tolerance = vmath.v3is_within_tolerance(b1, b2, tan_split_tol_sq)
            return tangent_within_tolerance and binormal_within_tolerance

        def potential_accumulation_vertexes(vertex_index, split_map):
            """Iterator to consider all potential accumulation vertexes."""
            yield (vertex_index, vertex_index)
            for (original_index, clone_index) in split_map:
                if original_index == vertex_index:
                    yield (original_index, clone_index)

        for (original_index, index) in potential_accumulation_vertexes(vertex_index, split_map):
            if tangents_within_tolerance(self.tangents[index], self.binormals[index],
                                         tangent, binormal, tan_split_tol_sq):
                self.tangents[index] = vmath.v3add(self.tangents[index], tangent)
                self.binormals[index] = vmath.v3add(self.binormals[index], binormal)
                update_primitive_vertexes(self.primitives, prim_index, original_index, index)
                break
        else:
            # We need to split the vertex to start accumulating a different set of tangents.
            clone_index = self._clone_vertex_with_new_tangents(prim_index, vertex_index, tangent, binormal)
            update_primitive_vertexes(self.primitives, prim_index, vertex_index, clone_index)
            split_map.append( (vertex_index, clone_index) )
            LOG.debug("Splitting vertex:%i --> %i primitive[%i] is now:%s", vertex_index, clone_index, prim_index,
                      self.primitives[prim_index])
            LOG.debug("N:%s B:%s T:%s", self.normals[clone_index], self.binormals[clone_index],
                      self.tangents[clone_index])

    # pylint: disable=R0914
    def _generate_tangents_for_triangle(self, prim, pos_tol, zero_tol):
        """Generate binormals and tangents for a primitive."""
        du = [0, 0, 0]
        dv = [0, 0, 0]
        (i1, i2, i3) = prim                                                                     # Primitive indexes
        (v1, v2, v3) = (self.positions[i1], self.positions[i2], self.positions[i3])             # Vertex positions
        uvs = self.uvs[0]
        (uv1, uv2, uv3) = (uvs[i1], uvs[i2], uvs[i3])                                           # Vertex UVs
        (e21, e31, e32) = (vmath.v3sub(v2, v1), vmath.v3sub(v3, v1), vmath.v3sub(v3, v2))       # Generate edges
        # Ignore degenerates
        if (vmath.v3is_zero(e21, pos_tol) or vmath.v3is_zero(e31, pos_tol) or vmath.v3is_zero(e32, pos_tol)):
            LOG.warning("%s: Found degenerate triangle:%s", "_generate_tangents_for_triangle", (i1, i2, i3))
        else:
            # Calculate tangent and binormal
            edge1 = [e21[0], uv2[0] - uv1[0], uv2[1] - uv1[1]]
            edge2 = [e31[0], uv3[0] - uv1[0], uv3[1] - uv1[1]]
            cp = vmath.v3cross(edge1, edge2)
            if not vmath.iszero(cp[0], zero_tol):
                du[0] = -cp[1] / cp[0]
                dv[0] = -cp[2] / cp[0]
            edge1[0] = e21[1] # y, s, t
            edge2[0] = e31[1]
            cp = vmath.v3cross(edge1, edge2)
            if not vmath.iszero(cp[0], zero_tol):
                du[1] = -cp[1] / cp[0]
                dv[1] = -cp[2] / cp[0]
            edge1[0] = e21[2] # z, s, t
            edge2[0] = e31[2]
            cp = vmath.v3cross(edge1, edge2)
            if not vmath.iszero(cp[0], zero_tol):
                du[2] = -cp[1]/cp[0]
                dv[2] = -cp[2]/cp[0]
        return (du, dv)
    # pylint: enable=R0914

    def generate_tangents(self, pos_tol=DEFAULT_POSITION_TOLERANCE,
                                zero_tol=DEFAULT_ZERO_TOLERANCE,
                                tan_split_tol=DEFAULT_TANGENT_SPLIT_TOLERANCE):
        """Generate a NBT per vertex."""
        if 0 == len(self.uvs[0]): # We can't generate nbts without uvs
            LOG.debug("Can't generate nbts without uvs:%i", len(self.uvs[0]))
            return
        num_vertices = len(self.positions)
        self.tangents = [ (0, 0, 0) ] * num_vertices
        self.binormals = [ (0, 0, 0) ] * num_vertices

        # Split map for recording pairs of integers that represent which vertexes have been split.
        partition_vertices = True
        split_map = [ ]
        tan_split_tol_sq = (tan_split_tol * tan_split_tol)

        for prim_index, prim in enumerate(self.primitives):
            (tangent, binormal) = self._generate_tangents_for_triangle(prim, pos_tol, zero_tol)
            (i1, i2, i3) = prim
            if partition_vertices:
                self._split_vertex_with_new_tangents(i1, prim_index, split_map, tangent, binormal, tan_split_tol_sq)
                self._split_vertex_with_new_tangents(i2, prim_index, split_map, tangent, binormal, tan_split_tol_sq)
                self._split_vertex_with_new_tangents(i3, prim_index, split_map, tangent, binormal, tan_split_tol_sq)
            else:
                # Accumulate tangent and binormal
                self.tangents[i1] = vmath.v3add(self.tangents[i1], tangent)
                self.tangents[i2] = vmath.v3add(self.tangents[i2], tangent)
                self.tangents[i3] = vmath.v3add(self.tangents[i3], tangent)
                self.binormals[i1] = vmath.v3add(self.binormals[i1], binormal)
                self.binormals[i2] = vmath.v3add(self.binormals[i2], binormal)
                self.binormals[i3] = vmath.v3add(self.binormals[i3], binormal)

    def normalize_tangents(self, dont_norm_tol=DEFAULT_DONT_NORMALIZE_TOLERANCE):
        """Normalize and clamp the new tangents and binormals."""
        zero = (0, 0, 0)

        tangents = [ ]
        for i, t in enumerate(self.tangents):
            if (vmath.v3lengthsq(t) > dont_norm_tol): # Ensure the tangent isn't tiny before normalizing it.
                tangents.append(vmath.v3unitcube_clamp(vmath.v3normalize(t)))
            else:
                LOG.warning("%s: Found vertex[%i] with tangent < normalizable tolerance[%g]:%s",
                            "normalize_tangents", i, dont_norm_tol, t)
                tangents.append(zero)
        self.tangents = tangents

        binormals = [ ]
        for i, b in enumerate(self.binormals):
            if (vmath.v3lengthsq(b) > dont_norm_tol):
                binormals.append(vmath.v3unitcube_clamp(vmath.v3normalize(b)))
            else:
                LOG.warning("%s: Found vertex[%i] with binormal < normalizable tolerance[%g]:%s",
                            "normalize_tangents", i, dont_norm_tol, b)
                binormals.append(zero)
        self.binormals = binormals

    def smooth_tangents(self, include_uv_tol=False,
                              root_node=None,
                              pos_tol=DEFAULT_POSITION_TOLERANCE,
                              nor_smooth_tol=DEFAULT_NORMAL_SMOOTH_TOLERANCE,
                              uv_tol=DEFAULT_UV_TOLERANCE):
        """Smooth the tangents of vertices with similar positions."""
        def tangents_are_similar(t1, t2, b1, b2, nor_smooth_tol):
            """Test if both the tangents and binormals are similar."""
            tangent_similar = vmath.v3is_similar(t1, t2, nor_smooth_tol)
            binormal_similar = vmath.v3is_similar(b1, b2, nor_smooth_tol)
            return tangent_similar and binormal_similar

        if not root_node:
            if not self.kdtree:
                # Create a kd-tree to optimize the smoothing performance
                self.kdtree = pointmap.build_kdtree(self.positions)
            root_node = self.kdtree

        uvs = self.uvs[0]
        for i, p in enumerate(self.positions):
            original_tangent = self.tangents[i]
            original_binormal = self.binormals[i]
            accumulate_tangent = (0, 0, 0)
            accumulate_binormal = (0, 0, 0)
            accumulated_indexes = [ ]

            # Generate a list of indexes for the positions close to the evaluation vertex.
            if include_uv_tol:
                uv = uvs[i]
                similiar_positions_indexes = root_node.points_within_uv_distance(self.positions, p, pos_tol,
                                                                                 uvs, uv, uv_tol)
            else:
                similiar_positions_indexes = root_node.points_within_distance(self.positions, p, pos_tol)

            for i in similiar_positions_indexes:
                this_tangent = self.tangents[i]
                this_binormal = self.binormals[i]
                if tangents_are_similar(this_tangent, original_tangent,
                                        this_binormal, original_binormal, nor_smooth_tol):
                    accumulate_tangent = vmath.v3add(accumulate_tangent, this_tangent)
                    accumulate_binormal = vmath.v3add(accumulate_binormal, this_binormal)
                    accumulated_indexes.append(i)
            smooth_tangent = vmath.v3unitcube_clamp(vmath.v3normalize(accumulate_tangent))
            smooth_binormal = vmath.v3unitcube_clamp(vmath.v3normalize(accumulate_binormal))
            for i in accumulated_indexes:
                self.tangents[i] = smooth_tangent
                self.binormals[i] = smooth_binormal

    def generate_normals_from_tangents(self, zero_tol=DEFAULT_ZERO_TOLERANCE,
                                             dont_norm_tol=DEFAULT_DONT_NORMALIZE_TOLERANCE):
        """Create a new normal from the tangent and binormals."""
        if not len(self.tangents) or not len(self.binormals): # We can't generate normals without nbts
            LOG.debug("Can't generate normals from nbts without tangets:%i and binormals:%i",
                      len(self.tangents), len(self.binormals))
            return
        num_vertices = len(self.normals)
        assert(num_vertices == len(self.tangents))
        assert(num_vertices == len(self.binormals))
        # Regenerate the vertex normals from the new tangents and binormals
        for i in range(num_vertices):
            normal = self.normals[i]
            cp = vmath.v3cross(self.tangents[i], self.binormals[i])
            # Keep vertex normal if the tangent and the binormal are paralel
            if (vmath.v3lengthsq(cp) > dont_norm_tol):
                cp = vmath.v3normalize(cp)
                # Keep vertex normal if new normal is *somehow* in the primitive plane
                cosangle = vmath.v3dot(cp, normal)
                if not vmath.iszero(cosangle, zero_tol):
                    if cosangle < 0:
                        self.normals[i] = vmath.v3neg(cp)
                    else:
                        self.normals[i] = cp

    def flip_primitives(self):
        """Change winding order"""
        self.primitives = [ (i1, i3, i2) for (i1, i2, i3) in self.primitives ]

    def mirror_in(self, axis="x", flip=True):
        """Flip geometry in axis."""
        if axis == "x":
            self.positions = [ (-x, y, z) for (x, y, z) in self.positions ]
            self.normals = [ (-x, y, z) for (x, y, z) in self.normals ]
        elif axis == "y":
            self.positions = [ (x, -y, z) for (x, y, z) in self.positions ]
            self.normals = [ (x, -y, z) for (x, y, z) in self.normals ]
        elif axis == "z":
            self.positions = [ (x, y, -z) for (x, y, z) in self.positions ]
            self.normals = [ (x, y, -z) for (x, y, z) in self.normals ]
        if flip:
            self.flip_primitives()

    ###################################################################################################################

    def remove_redundant_vertexes(self):
        """Remove redundant vertex indexes from the element streams if unused by the primitives."""
        mapping = { }
        new_index = 0
        for (i1, i2, i3) in self.primitives:
            if i1 not in mapping:
                mapping[i1] = new_index
                new_index += 1
            if i2 not in mapping:
                mapping[i2] = new_index
                new_index += 1
            if i3 not in mapping:
                mapping[i3] = new_index
                new_index += 1
        old_index = len(self.positions)
        if old_index != new_index:
            LOG.info("Remapping:remapping vertexes from %i to %i", old_index, new_index)

        def __remap_stream(source, size, mapping):
            """Remap vertex attribute stream."""
            if len(source) > 0:
                target = [0] * size
                for k, v in mapping.items():
                    target[v] = source[k]
                return target
            return [ ]

        self.positions = __remap_stream(self.positions, new_index, mapping)
        for uvs in self.uvs:
            uvs[:] = __remap_stream(uvs, new_index, mapping)
        self.normals = __remap_stream(self.normals, new_index, mapping)
        self.tangents = __remap_stream(self.tangents, new_index, mapping)
        self.binormals = __remap_stream(self.binormals, new_index, mapping)
        self.colors = __remap_stream(self.colors, new_index, mapping)
        self.skin_indices = __remap_stream(self.skin_indices, new_index, mapping)
        self.skin_weights = __remap_stream(self.skin_weights, new_index, mapping)

        primitives = [ ]
        for (i1, i2, i3) in self.primitives:
            primitives.append( (mapping[i1], mapping[i2], mapping[i3]) )
        self.primitives = primitives

    ###################################################################################################################

    def stitch_vertices(self):
        """Combine equal vertices together, adjusting indices of primitives where appropriate
           Any other vertex data like normals, tangents, colors are ignored"""

        num_points = len(self.positions)
        points = sorted(enumerate(self.positions), key=lambda (_, x): x)

        mapping = [0] * num_points
        new_index = -1
        prev_p = None
        for (index, p) in points:
            if p != prev_p:
                new_index += 1
                prev_p = p
            mapping[index] = new_index

        self.primitives = [(mapping[i1], mapping[i2], mapping[i3]) for (i1, i2, i3) in self.primitives]
        new_positions = [0] * (new_index + 1)
        for (i, to) in enumerate(mapping):
            new_positions[to] = self.positions[i]
        self.positions = new_positions

    ###################################################################################################################

    def is_convex(self, positions=None, primitives=None):
        """Check if a mesh is convex by validating no vertices lie in front of the planes defined by its faces."""
        positions = positions or self.positions
        primitives = primitives or self.primitives
        for (i1, i2, i3) in primitives:
            v1 = positions[i1]
            v2 = positions[i2]
            v3 = positions[i3]

            edge1 = vmath.v3sub(v1, v3)
            edge2 = vmath.v3sub(v2, v3)
            normal = vmath.v3normalize(vmath.v3cross(edge1, edge2))

            for p in positions:
                dist = vmath.v3dot(vmath.v3sub(p, v1), normal)
                if dist > vmath.PRECISION:
                    return False
        return True

    def simply_closed(self, primitives=None):
        """Determine if a connected mesh is closed defined by triangle indexes
           in sense that it defines the boundary of a closed region of space without any
           possible dangling triangles on boundary.

           We assume that the triangle mesh does not have any ugly self intersections."""
        primitives = primitives or self.primitives
        # We do this by counting the number of triangles on each triangle edge
        # Specifically check that this value is exactly 2 for every edge.1
        edges = { }
        def _inc(a, b):
            """Increment edge count for vertex indices a, b.
               Return True if edge count has exceeded 2"""
            if a > b:
                return _inc(b, a)
            if (a, b) in edges:
                edges[(a, b)] += 1
            else:
                edges[(a, b)] = 1
            return edges[(a, b)] > 2

        for (i1, i2, i3) in primitives:
            if _inc(i1, i2):
                return False
            if _inc(i2, i3):
                return False
            if _inc(i3, i1):
                return False

        for (_, v) in edges.items():
            if v != 2:
                return False

        return True

    def is_planar(self, positions=None, tolerance=DEFAULT_PLANAR_TOLERANCE):
        """Determine if mesh is planar; that all vertices lie in the same plane.
           If positions argument is not supplied, then self.positions is used"""
        positions = positions or self.positions
        if len(positions) <= 3:
            return True

        p0 = positions[0]
        edge1 = vmath.v3sub(positions[1], p0)
        edge2 = vmath.v3sub(positions[2], p0)
        normal = vmath.v3normalize(vmath.v3cross(edge1, edge2))

        for p in positions:
            distance = vmath.v3dot(vmath.v3sub(p, p0), normal)
            if (distance * distance) > tolerance:
                return False

        return True

    def is_convex_planar(self, positions=None):
        """Determine if a planar mesh is convex; taking virtual edge normals into account"""
        positions = positions or self.positions
        if len(positions) <= 3:
            return True

        p0 = positions[0]
        edge1 = vmath.v3sub(positions[1], p0)
        edge2 = vmath.v3sub(positions[2], p0)
        normal = vmath.v3normalize(vmath.v3cross(edge1, edge2))

        for (i, p) in enumerate(positions):
            j = (i + 1) if (i < len(positions) - 1) else 0
            q = positions[j]

            edge3 = vmath.v3sub(q, p)
            edge_normal = vmath.v3cross(normal, edge3)

            for w in positions:
                if vmath.v3dot(vmath.v3sub(w, p), edge_normal) < -vmath.PRECISION:
                    return False

        return True

    def connected_components(self):
        """Determine connected components of mesh, returning list of set of vertices and primitives."""
        # Perform this algorithm with a disjoint set forest.
        # Initialise components: [index, parent_index, rank, component]
        components = [[i, 0] for i in range(len(self.positions))]

        def _find(x):
            """Find root note in disjoint set forest, compressing path to root."""
            if components[x][0] == x:
                return x
            else:
                root = x
                stack = [ ]
                while components[root][0] != root:
                    stack.append(root)
                    root = components[root][0]
                for y in stack:
                    components[y][0] = root
                return root

        def _unify(x, y):
            """Unify two components in disjoint set forest by rank."""
            x_root = _find(x)
            y_root = _find(y)
            if x_root != y_root:
                xc = components[x_root]
                yc = components[y_root]
                if xc[1] < yc[1]:
                    xc[0] = y_root
                elif xc[1] > yc[1]:
                    yc[0] = x_root
                else:
                    yc[0] = x_root
                    xc[1] += 1

        # Unify components based on adjacency information inferred through shared vertices in primitives
        for (i1, i2, i3) in self.primitives:
            _unify(i1, i2)
            _unify(i2, i3)

        # Return list of all components associated with each root.
        ret = [ ]
        for c in [y for y in range(len(self.positions)) if _find(y) == y]:
            m = Mesh()
            m.positions = self.positions[:]
            m.primitives = [(i1, i2, i3) for (i1, i2, i3) in self.primitives if _find(i1) == c]

            m.remove_redundant_vertexes()
            ret.append((m.positions, m.primitives))

        return ret

    # pylint: disable=R0914
    def make_planar_convex_hull(self, positions=None, tangent_tolerance=DEFAULT_TANGENT_PROJECTION_TOLERANCE):
        """Convert set of co-planar positions into a minimal set of positions required to form their convex
           hull, together with a set of primitives representing one side of the hulls' surface as a
           new Mesh"""
        positions = positions or self.positions
        # Use a 2D Graham Scan with projections of positions onto their maximal plane.
        # Time complexity: O(nh) for n positions and h out positions.

        # Determine maximal plane for projection.
        edge1 = vmath.v3sub(positions[1], positions[0])
        edge2 = vmath.v3sub(positions[2], positions[0])
        (n0, _, n2) = n = vmath.v3cross(edge1, edge2)

        # compute plane tangents.
        # epsilon chosen with experiment
        if (n0 * n0) + (n2 * n2) < tangent_tolerance:
            t = (1, 0, 0)
        else:
            t = (-n2, 0, n0)
        u = vmath.v3cross(n, t)

        # Project to tangents
        projs = [(vmath.v3dot(p, t), vmath.v3dot(p, u)) for p in positions]

        # Find first vertex on hull as minimal lexicographically ordered projection
        i0 = 0
        minp = projs[0]
        for i in range(1, len(projs)):
            if projs[i] < minp:
                i0 = i
                minp = projs[i]

        # Map from old vertex indices to new index for those vertices used by hull
        outv = { i0: 0 }
        new_index = 1

        # List of output triangles.
        outtriangles = [ ]
        fsti = i0
        (p0x, p0y) = minp
        while True:
            i1 = -1
            for i in range(len(projs)):
                if i == i0:
                    continue

                (px, py) = projs[i]
                plsq = ((px - p0x) * (px - p0x)) + ((py - p0y) * (py - p0y))
                if i1 == -1:
                    i1 = i
                    maxp = (px, py)
                    maxplsq = plsq
                    continue

                # If this is not the first vertex tested, determine if new vertex makes
                # A right turn looking in direction of edge, or is further in same direction.
                (qx, qy) = maxp
                turn = ((qx - p0x) * (py - p0y)) - ((qy - p0y) * (px - p0x))
                if turn < 0 or (turn == 0 and plsq > maxplsq):
                    i1 = i
                    maxp = (px, py)
                    maxplsq = plsq

            # Append i1 vertex to hull
            if i1 in outv:
                break

            outv[i1] = new_index
            new_index += 1

            # Form triangle (fsti, i0, i1)
            # If i0 != fsti
            if i0 != fsti:
                outtriangles.append((fsti, i0, i1))

            i0 = i1
            (p0x, p0y) = projs[i1]

        # Compute output hull.
        mesh = Mesh()
        mesh.positions = [0] * len(outv.items())
        for i, j in outv.items():
            mesh.positions[j] = positions[i]
        mesh.primitives = [(outv[i1], outv[i2], outv[i3]) for (i1, i2, i3) in outtriangles]

        return mesh
    # pylint: enable=R0914

    # pylint: disable=R0914
    def make_convex_hull(self, positions=None, collinear_tolerance=DEFAULT_COLLINEAR_TOLERANCE,
                               coplanar_tolerance=DEFAULT_COPLANAR_TOLERANCE):
        """Convert set of positions into a minimal set of positions required to form their convex hull
           Together with a set of primitives representing a triangulation of the hull's surface as a
           new Mesh"""
        positions = positions or self.positions
        # Use a 3D generalisation of a Graham Scan to facilitate a triangulation of the hull in generation.
        # Time complexity: O(nh) for n positions, and h out-positions.

        # Find first vertex on hull as minimal lexicographically ordered position
        i0 = 0
        minp = positions[0]
        for i in range(1, len(positions)):
            if positions[i] < minp:
                i0 = i
                minp = positions[i]

        # Find second vertex by performing a 2D graham scan step on the xy-plane projections of positions.
        i1 = -1
        (cos1, lsq1) = (-2, 0) # will always be overriden as cos(theta) > -2
        (p0x, p0y, _) = minp
        for i in range(len(positions)):
            if i == i0:
                continue

            (px, py, _) = positions[i]
            dx = px - p0x
            dy = py - p0y
            lsq = (dx * dx) + (dy * dy)
            if lsq == 0:
                if i1 == -1:
                    i1 = i
                continue

            cos = dy / math.sqrt(lsq)
            if cos > cos1 or (cos == cos1 and lsq > lsq1):
                cos1 = cos
                lsq1 = lsq
                i1 = i

        # Dictionary of visited edges to avoid duplicates
        # List of open edges to be visited by graham scan
        closedset = set()
        openset = [ (i0, i1), (i1, i0) ]

        # Mapping from old vertex index to new index for those vertices used by hull.
        outv = { i0: 0, i1: 1 }
        new_index = 2

        # Output triangles for hull
        outtriangles = [ ]

        while len(openset) > 0:
            (i0, i1) = openset.pop()
            if (i0, i1) in closedset:
                continue

            # Find next vertex on hull to form triangle with.
            i2 = -1

            p0 = positions[i0]
            edge = vmath.v3sub(positions[i1], p0)
            isq = 1.0 / vmath.v3lengthsq(edge)

            for i in range(len(positions)):
                if i == i0 or i == i1:
                    continue

                p = positions[i]
                # Find closest point on line containing the edge to determine vector to p
                # Perpendicular to edge, this is not necessary for computing the turn
                # since the value of 'turn' computed is actually the same whether we do this
                # or not, however it is needed to be able to sort equal turn vertices
                # by distance.
                t = vmath.v3dot(vmath.v3sub(p, p0), edge) * isq
                pedge = vmath.v3sub(p, vmath.v3add(p0, vmath.v3muls(edge, t)))

                # Ignore vertex if |pedge| = 0, thus ignoring vertices on the edge itself
                # And so avoid generating degenerate triangles.
                #
                # epsilon chosen by experiment
                plsq = vmath.v3lengthsq(pedge)
                if plsq <= collinear_tolerance:
                    continue

                if i2 == -1:
                    i2 = i
                    maxpedge = pedge
                    maxplsq = plsq
                    maxt = t
                    continue

                # If this is not the first vertex tested, determine if new vertex makes
                # A right turn looking in direction of edge, or is further in same direction.
                #
                # We require a special case when pedge, and maxpedge are coplanar with edge
                # As the computed turn will be 0 and we must check if the cross product
                # Is facing into the hull or outside to determine left/right instead.
                axis = vmath.v3cross(pedge, maxpedge)
                coplanar = vmath.v3dot(pedge, vmath.v3cross(edge, maxpedge))
                # epsilon chosen by experiment
                if (coplanar * coplanar) <= coplanar_tolerance:
                    # Special case for coplanar pedge, maxpedge, edge
                    #
                    # if edges are in same direction, base on distance.
                    if vmath.v3dot(pedge, maxpedge) >= 0:
                        if plsq > maxplsq or (plsq == maxplsq and t > maxt):
                            i2 = i
                            maxpedge = pedge
                            maxplsq = plsq
                            maxt = t
                    else:
                        axis = vmath.v3cross(vmath.v3sub(p, p0), edge)
                        # Check if axis points into the hull.
                        internal = True
                        for p in positions:
                            if vmath.v3dot(axis, vmath.v3sub(p, p0)) < 0:
                                internal = False
                                break

                        if internal:
                            i2 = i
                            maxpedge = pedge
                            maxplsq = plsq
                            maxt = t
                else:
                    turn = vmath.v3dot(axis, edge)
                    # epsilon chosen by experiment
                    if turn < 0 or (turn <= collinear_tolerance and plsq > maxplsq):
                        i2 = i
                        maxpedge = pedge
                        maxplsq = plsq
                        maxt = t

            # Append i2 vertex to hull
            if i2 not in outv:
                outv[i2] = new_index
                new_index += 1

            # Form triangle iff no edge is closed.
            if ((i0, i1) not in closedset and
                (i1, i2) not in closedset and
                (i2, i0) not in closedset):

                outtriangles.append((i0, i1, i2))
                # Mark visited edges. Open new edges.
                closedset.add((i0, i1))
                closedset.add((i1, i2))
                closedset.add((i2, i0))

                openset.append((i2, i1))
                openset.append((i0, i2))

        # cnt does not 'need' to be len(positions) for convex hull to have succeeded
        #   but numerical issues with not using say fixed point means that we cannot
        #   be sure of success if it is not equal.
        # Obvious side effect is input mesh must already be a convex hull with no
        #   unnecessary vertices.
        cnt = len(outv.items())
        if cnt != len(positions):
            return None

        # Compute output mesh.
        mesh = Mesh()
        mesh.positions = [0] * cnt
        for (i, j) in outv.items():
            mesh.positions[j] = positions[i]
        mesh.primitives = [(outv[i1], outv[i2], outv[i3]) for (i1, i2, i3) in outtriangles]

        # Ensure algorithm has not failed!
        if not mesh.is_convex() or not mesh.simply_closed():
            return None

        return mesh
    # pylint: enable=R0914

    def extend_mesh(self, positions, primitives):
        """Extend mesh with extra set of positions and primitives defiend relative to positions"""
        offset = len(self.positions)
        self.positions.extend(positions)
        self.primitives.extend([(i1 + offset, i2 + offset, i3 + offset) for (i1, i2, i3) in primitives])

    def convex_hulls(self, max_components=-1, allow_non_hulls=False,
                           planar_vertex_count=DEFAULT_PLANAR_HULL_VERTEX_THRESHOLD):
        """Split triangle mesh into set of unconnected convex hulls.

           If max_components != -1, then None will be returned should the number
           of connected components exceed this value.

           If allow_non_hulls is False, and any component of the mesh was not able
           to be converted then None will be returned.

           No other vertex data is assumed to exist, and mesh is permitted to be
           mutated.

           The return value is a tuple ([Mesh], Mesh) for the list of convex hulls
           computed, and an additional mesh representing the remainder of the mesh
           which could not be converted (If allow_non_hulls is False, then this
           additional mesh will always be None, otherwise it may still be None
           if all of the mesh was able to be converted)."""
        self.stitch_vertices()
        self.remove_degenerate_primitives()
        self.remove_redundant_vertexes()

        components = self.connected_components()
        if max_components != -1 and len(components) > max_components:
            return None

        if allow_non_hulls:
            triangles = Mesh()
            triangles.positions = [ ]
            triangles.primitives = [ ]

        ret = [ ]
        for (vertices, primitives) in components:
            convex = self.is_convex(vertices, primitives)
            closed = self.simply_closed(primitives)
            planar = self.is_planar(vertices)

            if convex and planar:
                if self.is_convex_planar(vertices) and len(vertices) >= planar_vertex_count:
                    print "Converted to planar convex hull!"
                    ret.append(self.make_planar_convex_hull(vertices))
                else:
                    if allow_non_hulls:
                        triangles.extend_mesh(vertices, primitives)
                    else:
                        return None

            elif convex and closed:
                mesh = self.make_convex_hull(vertices)
                if mesh == None:
                    if allow_non_hulls:
                        print "Failed to turn convex closed mesh into convex hull!"
                        triangles.extend_mesh(vertices, primitives)
                    else:
                        return None
                else:
                    # Ensure that convex hull can be re-computed correctly as this will be performed
                    # By WebGL physics device.
                    if mesh.make_convex_hull() == None:
                        if allow_non_hulls:
                            print "Convex hull failed to be re-computed!"
                            triangles.extend_mesh(vertices, primitives)
                        else:
                            return None
                    else:
                        print "Converted to convex hull!"
                        ret.append(mesh)

            else:
                # Cannot convert component to a convex hull.
                if allow_non_hulls:
                    triangles.extend_mesh(vertices, primitives)
                else:
                    return None

        if len(triangles.positions) == 0:
            triangles = None

        return (ret, triangles)

# pylint: enable=R0902
# pylint: enable=R0904

#######################################################################################################################

# pylint: disable=C0111
def __generate_test_square(json_asset):

    def __generate_square_t():
        mesh = Mesh()
        mesh.positions.extend( [ (0, 0, 0), (1, 0, 0), (1, 1, 1), (0, 1, 1), (2, 0, 0), (2, 1, 1) ] )
        mesh.uvs[0].extend( [ (0, 0), (1, 0), (1, 1), (0, 1), (0, 0), (0, 1) ] )
        indexes = [ ]
        indexes.extend( [ 0, 1, 2, 0, 2, 3, 1, 4, 5, 1, 5, 2 ] )
        return (mesh, indexes)

    def __generate_square_b():
        mesh = Mesh()
        mesh.positions.extend( [ (0, 2, 2), (1, 2, 2), (1, 3, 3), (0, 3, 3), (2, 2, 2), (2, 3, 3) ] )
        mesh.uvs[0].extend( [ (0, 0), (0, 1), (1, 1), (1, 0), (0, 0), (1, 0) ] )
        indexes = [ ]
        indexes.extend( [ 0, 1, 2, 0, 2, 3, 1, 4, 5, 1, 5, 2 ] )
        return (mesh, indexes)

    def __generate_split_square_t():
        mesh = Mesh()
        mesh.positions.extend( [ (0, 4, 4), (1, 4, 4), (1, 5, 5), (0, 5, 5), (2, 4, 4), (2, 5, 5),
                                 (1, 4, 4), (1, 5, 5) ] )
        mesh.uvs[0].extend( [ (0, 0), (1, 0), (1, 1), (0, 1), (0, 0), (0, 1),
                              (1, 0), (1, 1) ] )
        indexes = [ ]
        indexes.extend( [ 0, 1, 2, 0, 2, 3, 6, 4, 5, 6, 5, 7 ] )
        return (mesh, indexes)

    def __generate_split_square_b():
        mesh = Mesh()
        mesh.positions.extend( [ (0, 6, 6), (1, 6, 6), (1, 7, 7), (0, 7, 7), (2, 6, 6), (2, 7, 7),
                                 (1, 6, 6), (1, 7, 7) ] )
        mesh.uvs[0].extend( [ (0, 0), (0, 1), (1, 1), (1, 0), (0, 0), (1, 0),
                              (0, 1), (1, 1) ] )
        indexes = [ ]
        indexes.extend( [ 0, 1, 2, 0, 2, 3, 6, 4, 5, 6, 5, 7 ] )
        return (mesh, indexes)

    def __generate_control_square_t():
        r2 = 1 / math.sqrt(2)
        mesh = Mesh()
        mesh.positions.extend( [ (0, 8, 8), (1, 8, 8), (1, 9, 9), (0, 9, 9),
                                 (1, 8, 8), (2, 8, 8), (2, 9, 9), (1, 9, 9) ] )
        mesh.uvs[0].extend( [ (0, 0), (1, 0), (1, 1), (0, 1),
                              (1, 0), (0, 0), (0, 1), (1, 1) ] )
        mesh.tangents.extend( [ (1, 0, 0), (1, 0, 0), (1, 0, 0), (1, 0, 0),
                                (-1, 0, 0), (-1, 0, 0), (-1, 0, 0), (-1, 0, 0) ] )
        mesh.binormals.extend( [ (0, r2, r2), (0, r2, r2), (0, r2, r2), (0, r2, r2),
                                 (0, r2, r2), (0, r2, r2), (0, r2, r2), (0, r2, r2) ] )
        indexes = [ ]
        indexes.extend( [ 0, 1, 2, 0, 2, 3, 4, 5, 6, 4, 6, 7 ] )
        return (mesh, indexes)

    def __generate_control_square_b():
        r2 = 1 / math.sqrt(2)
        mesh = Mesh()
        mesh.positions.extend( [ (0, 10, 10), (1, 10, 10), (1, 11, 11), (0, 11, 11),
                                 (1, 10, 10), (2, 10, 10), (2, 11, 11), (1, 11, 11) ] )
        mesh.uvs[0].extend( [ (0, 0), (0, 1), (1, 1), (1, 0),
                              (0, 1), (0, 0), (1, 0), (1, 1) ] )
        mesh.tangents.extend( [ (0, r2, r2), (0, r2, r2), (0, r2, r2), (0, r2, r2),
                                (0, r2, r2), (0, r2, r2), (0, r2, r2), (0, r2, r2) ] )
        mesh.binormals.extend( [ (1, 0, 0), (1, 0, 0), (1, 0, 0), (1, 0, 0),
                                 (-1, 0, 0), (-1, 0, 0), (-1, 0, 0), (-1, 0, 0) ] )
        indexes = [ ]
        indexes.extend( [ 0, 1, 2, 0, 2, 3, 4, 5, 6, 4, 6, 7 ] )
        return (mesh, indexes)

    def __generate_square((a, i), (s, n), j):
        a.generate_primitives(i)
        a.generate_normals()
        if len(a.tangents) == 0:
            a.generate_smooth_nbts()
        j.attach_shape(s)
        n = NodeName(n)
        j.attach_node(n)
        j.attach_node_shape_instance(n, s, s, m)
        j.attach_positions(a.positions, s)
        j.attach_nbts(a.normals, a.tangents, a.binormals, s)
        j.attach_uvs(a.uvs[0], s)
        j.attach_surface(a.primitives, JsonAsset.SurfaceTriangles, s)

    m = 'material-0'
    e = 'effect-0'
    json_asset.attach_effect(e, 'normalmap')
    json_asset.attach_material(m, e)
    json_asset.attach_texture(m, 'diffuse', '/assets/checker.png')
    json_asset.attach_texture(m, 'normal_map', '/assets/monkey.png')
    __generate_square(__generate_square_t(), ('shape-0', 'node-0'), json_asset)
    __generate_square(__generate_square_b(), ('shape-1', 'node-1'), json_asset)
    __generate_square(__generate_split_square_t(), ('shape-2', 'node-2'), json_asset)
    __generate_square(__generate_split_square_b(), ('shape-3', 'node-3'), json_asset)
    __generate_square(__generate_control_square_t(), ('shape-4', 'node-4'), json_asset)
    __generate_square(__generate_control_square_b(), ('shape-5', 'node-5'), json_asset)

def __generate_test_cube():
    def add_quad_face(v, m, primitives):
        """Append a two triangle quad to the mesh."""
        offset = len(m.positions)
        m.positions.extend( [ v[0], v[1], v[2], v[3] ] )
        m.uvs[0].extend( [ (1, 1), (0, 1), (0, 0), (1, 0) ] )
        primitives.extend( [offset, offset + 2, offset + 1, offset, offset + 3, offset + 2] )

    indexes = [ ]
    mesh = Mesh()
    v = [ (-1, -1, -1), (-1, -1,  1), (-1,  1,  1), (-1,  1, -1),
          ( 1, -1, -1), ( 1, -1,  1), ( 1,  1,  1), ( 1,  1, -1) ]
    add_quad_face( [ v[0], v[1], v[2], v[3] ], mesh, indexes)
    add_quad_face( [ v[4], v[0], v[3], v[7] ], mesh, indexes)
    add_quad_face( [ v[5], v[4], v[7], v[6] ], mesh, indexes)
    add_quad_face( [ v[1], v[5], v[6], v[2] ], mesh, indexes)
    add_quad_face( [ v[7], v[3], v[2], v[6] ], mesh, indexes)
    add_quad_face( [ v[1], v[0], v[4], v[5] ], mesh, indexes)

    mesh.generate_primitives(indexes)
    return mesh

# pylint: enable=C0111

if __name__ == "__main__":
    # pylint: disable=W0403
    from asset2json import JsonAsset
    from node import NodeName
    # pylint: enable=W0403
    logging.basicConfig(level=logging.INFO)

    J = JsonAsset()
    __generate_test_square(J)
    J.clean()
    JSON = J.json_to_string()
    with open("mesh.json", 'w') as output:
        output.write(JSON)
    print JSON
    J.log_metrics()
