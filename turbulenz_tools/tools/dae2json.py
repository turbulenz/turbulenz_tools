#!/usr/bin/python
# Copyright (c) 2010-2013 Turbulenz Limited
"""
Convert Collada (.dae) files into a Turbulenz JSON asset.
"""

# pylint: disable=C0302
# C0302 - Too many lines in module

import logging
LOG = logging.getLogger('asset')

# pylint: disable=W0404
try:
    from xml.etree import cElementTree as ElementTree
except ImportError:
    from xml.etree import ElementTree
# pylint: enable=W0404

from xml.parsers.expat import ExpatError

# pylint: disable=W0403
import sys
import math
import vmath
import subprocess

from stdtool import standard_parser, standard_main, standard_include, standard_json_out
from asset2json import JsonAsset, attach_skins_and_materials, remove_unreferenced_images

from node import NodeName
from mesh import Mesh
# pylint: enable=W0403

__version__ = '1.7.2'
__dependencies__ = ['asset2json', 'node', 'mesh']

def tag(t):
    return str(ElementTree.QName('http://www.collada.org/2005/11/COLLADASchema', t))

def untag(t):
    return t[len('{http://www.collada.org/2005/11/COLLADASchema}'):]

def pack(a, n):
    # Special case components of width 1
    if n == 1:
        return a[:]
    return [ tuple(a[i:i + n]) for i in range(0, len(a), n) ]

def _remove_prefix(line, prefix):
    if line.startswith(prefix):
        return line[len(prefix):]
    return line

#######################################################################################################################

def fix_sid(e, parent_id):
    e_id = e.get('id')
    if e_id:
        parent_id = e_id
    else:
        e_id = e.get('sid')
        if e_id:
            if parent_id:
                e_id = "%s/%s" % (parent_id, e_id)
            else:
                parent_id = e_id
            e.set('id', e_id)
    for child in e:
        fix_sid(child, parent_id)

def find_scoped_name(e_id, parent_id, name_map):
    name = name_map.get(e_id) or (parent_id and name_map.get("%s/%s" % (parent_id, e_id)))
    if name:
        return name
    return e_id

def find_scoped_node(e_id, parent_id, node_map):
    node = node_map.get(e_id) or (parent_id and node_map.get("%s/%s" % (parent_id, e_id)))
    if node:
        return node
    return None

def tidy_name(n, default=None, prefix=None):
    if n is None:
        return default
    if n is not None and n[0] == '#':
        n = n[1:]
    if prefix is not None:
        n = _remove_prefix(n, prefix)
        if n[0] == '-' or n[0] == '_':
            n = n[1:]

    return n

def tidy_value(value_text, value_type):
    if value_type == 'float':
        result = float(value_text)
    elif value_type == 'int':
        result = int(value_text)
    elif value_type == 'bool':
        value_bool = value_text.lower()
        if value_bool == 'true':
            result = True
        else:
            result = False
    elif value_type == 'color':
        result = [ float(x) for x in value_text.split() ]
    elif value_type.startswith('float'):
        result = [ float(x) for x in value_text.split() ]
    else:
        result = value_text.split()

    return result

REMAPPED_SEMANTICS = {
    'BITANGENT': 'BINORMAL',
    'BLEND_WEIGHT': 'BLENDWEIGHT',
    'INV_BIND_MATRIX': 'BLENDINDICES',
    'TEXBINORMAL': 'BINORMAL',
    'TEXTANGENT': 'TANGENT',
    'UV': 'TEXCOORD',
    'VERTEX': 'POSITION',
    'WEIGHT': 'BLENDWEIGHT'
}

def tidy_semantic(s, semantic_set=None):
    # Current runtime supported semantics are in src/semantic.h         #
    # ================================================================= #
    # 0  - ATTR0,               POSITION0,       POSITION               #
    # 1  - ATTR1,               BLENDWEIGHT0,    BLENDWEIGHT            #
    # 2  - ATTR2,               NORMAL0,         NORMAL                 #
    # 3  - ATTR3,               COLOR0,          COLOR                  #
    # 4  - ATTR4,               COLOR1,          SPECULAR               #
    # 5  - ATTR5,                                FOGCOORD, TESSFACTOR   #
    # 6  - ATTR6,               PSIZE0,          PSIZE                  #
    # 7  - ATTR7,               BLENDINDICES0,   BLENDINDICES           #
    # 8  - ATTR8,   TEXCOORD0,                   TEXCOORD               #
    # 9  - ATTR9,   TEXCOORD1                                           #
    # 10 - ATTR10,  TEXCOORD2                                           #
    # 11 - ATTR11,  TEXCOORD3                                           #
    # 12 - ATTR12,  TEXCOORD4                                           #
    # 13 - ATTR13,  TEXCOORD5                                           #
    # 14 - ATTR14,  TEXCOORD6,  TANGENT0,         TANGENT               #
    # 15 - ATTR15,  TEXCOORD7,  BINORMAL0,        BINORMAL              #
    # ================================================================= #
    # If the semantic isn't remapped just return it.
    semantic = REMAPPED_SEMANTICS.get(s, s)
    if semantic_set is not None:
        if semantic_set == '0' and semantic != 'TEXCOORD' and semantic != 'COLOR':
            pass
        elif semantic == 'TANGENT' or semantic == 'BINORMAL':
            pass
        else:
            semantic = semantic + semantic_set
    return semantic

def find_semantic(source_name, mesh_node_e):

    def _test_source(tags):
        if tags:
            for v_e in tags:
                for i in v_e.findall(tag('input')):
                    source = tidy_name(i.get('source'))
                    if (source is not None) and (source == source_name):
                        return tidy_semantic(i.get('semantic'), i.get('set'))
        return None

    semantic = _test_source(mesh_node_e.findall(tag('vertices')))
    if semantic is not None:
        return semantic

    semantic = _test_source(mesh_node_e.findall(tag('triangles')))
    if semantic is not None:
        return semantic

    semantic = _test_source(mesh_node_e.findall(tag('polylist')))
    if semantic is not None:
        return semantic

    semantic = _test_source(mesh_node_e.findall(tag('polygons')))
    if semantic is not None:
        return semantic

    return None

def invert_indices(indices, indices_per_vertex, vertex_per_polygon):
    # If indices_per_vertex = 3 and vertex_per_polygon = 3
    # [ 1, 2, 3, 4, 5, 6, 7, 8, 9 ] -> [ [7, 8, 9], [4, 5, 6], [1, 2, 3] ]
    vertex_indices = pack(indices, indices_per_vertex)
    if vertex_per_polygon == 2:
        polygon_indices = zip(vertex_indices[1::2], vertex_indices[::2])
    elif vertex_per_polygon == 3:
        polygon_indices = zip(vertex_indices[1::3], vertex_indices[2::3], vertex_indices[::3])
    elif vertex_per_polygon == 4:
        polygon_indices = zip(vertex_indices[1::4], vertex_indices[2::4], vertex_indices[3::4], vertex_indices[::4])
    else:
        LOG.error('Vertex per polygon unsupported:%i', vertex_per_polygon)

    return polygon_indices

def get_material_name(instance_e):
    bind_e = instance_e.find(tag('bind_material'))
    if bind_e is not None:
        technique_e = bind_e.find(tag('technique_common'))
        if technique_e is not None:
            material_e = technique_e.find(tag('instance_material'))
            if material_e is not None:
                return material_e.get('target')
    return None

def find_controller(source_name, controllers_e):
    for controller_e in controllers_e.findall(tag('controller')):
        controller_name = tidy_name(controller_e.get('id', controller_e.get('name')))
        if controller_name == source_name:
            return controller_e
    return None

def find_set_param(effect_e, name):
    for set_param_e in effect_e.findall(tag('setparam')):
        ref = set_param_e.get('ref')
        if ref is not None and ref == name:
            return set_param_e
    return None

def find_new_param(profile_e, name):
    for new_param_e in profile_e.findall(tag('newparam')):
        sid = new_param_e.get('sid')
        if sid is not None and sid == name:
            return new_param_e
    return None

def find_node(url, collada_e):
    # This might be better as an XPath of '//*[@id='url'] but the version of ElementTree in python
    # doesn't support attribute selection

    # Remove the # from the url
    if url is not None and url[0] == '#':
        node_id = url[1:]
    else:
        node_id = url
    # Find all nodes in the scene and look for the one with a matching id
    node_iterator = collada_e.getiterator(tag('node'))
    for node_e in node_iterator:
        if node_e.attrib.get('id') == node_id:
            return node_e
    return None

def find_name(name_map, id_name):
    if id_name in name_map:
        return name_map[id_name]
    return id_name


class UrlHandler(object):
    def __init__(self, asset_root, asset_path):
        if asset_root[-1] != '/':
            self.root = asset_root + '/'
        else:
            self.root = asset_root
        self.path = asset_path[:asset_path.rfind('/')]

    def tidy(self, u):
        u = _remove_prefix(u, 'file://')
        u = _remove_prefix(u, 'http://')
        u = _remove_prefix(u, '/')
        if u.startswith('./'):
            u = self.path + u[1:]
        if u.startswith('../'):
            path_index = -1
            u_index = 0
            while u.startswith('../', u_index):
                path_index = self.path.rfind('/', 0, path_index)
                if path_index == -1:
                    LOG.error('Unknown relative path:%s', u)
                    break
                u_index += 3
            u = self.path[:(path_index + 1)] + u[u_index:]
        u = _remove_prefix(u, self.root)
        if u[1] == ':' and u[2] == '/':
            u = u[3:]
        return u


#######################################################################################################################

def build_joint_hierarchy(start_joints, nodes, sid_inputs = False):

    def __find_node(node_name, node, use_sid):
        if use_sid:
            if node_name == node.sid:
                return node
        else:
            if node_name == node.id:
                return node
        for child in node.children:
            result = __find_node(node_name, child, use_sid)
            if result is not None:
                return result
        return None

    def __add_joint_hierarchy(node, parent_index, joints, joint_to_node_map):
        node_index = len(joints)
        if node in joint_to_node_map:
            orig_index = joint_to_node_map.index(node)
        else:
            orig_index = -1
        joints.append( { 'node':node, 'parent': parent_index, 'orig_index': orig_index } )
        for child in node.children:
            __add_joint_hierarchy(child, node_index, joints, joint_to_node_map)

    # Work out all the root nodes parenting any start joints
    hierarchies_affected = []
    joint_to_node_map = [ None ] * len(start_joints)
    for j, node_name in enumerate(start_joints):
        for root_name in nodes:
            node = __find_node(node_name, nodes[root_name], sid_inputs)
            if node is not None:
                joint_to_node_map[j] = node
                if not root_name in hierarchies_affected:
                    hierarchies_affected.append(root_name)

    # Given the hierarchy roots affected we need to build a hierarchical description
    hierarchy = []
    for n in range(0, len(hierarchies_affected)):
        __add_joint_hierarchy(nodes[hierarchies_affected[n]], -1, hierarchy, joint_to_node_map)

    return hierarchy

#######################################################################################################################

class Dae2Geometry(object):

    class Source(object):
        def __init__(self, values, semantic, name='unknown', stride=0, count=0):
            self.values = values
            self.semantic = semantic
            self.name = name
            self.stride = stride
            self.count = count
            self.zero_value = tuple([0] * stride)
            LOG.debug('SOURCE:%s:semantic:%s:stride:%i:count:%i', name, semantic, stride, count)

        def __repr__(self):
            return 'Dae2Geometry.Source<name:%s:semantic:%s:stride:%s:count:%s>' % \
                (self.name, self.semantic, self.stride, self.count)

    class Input(object):
        def __init__(self, semantic, source='unknown', offset=0):
            self.semantic = semantic
            self.source = source
            self.offset = offset
            LOG.debug('INPUT::source:%s:semantic:%s:offset:%i', source, semantic, offset)

        def __repr__(self):
            return 'Dae2Geometry.Input<semantic:%s:source:%s:offset:%s>' % (self.semantic, self.source, self.offset)

    class Surface(object):
        def __init__(self, sources, primitives, primitive_type):
            self.sources = sources
            self.primitives = primitives
            self.type = primitive_type

    def add_input(self, faces_e, shared_sources):
        # Offset N vertex inputs
        max_offset = 0
        sources = shared_sources.copy()
        if faces_e is not None:
            input_e = faces_e.findall(tag('input'))
            for i in input_e:
                semantic = i.get('semantic')
                if semantic != 'VERTEX': # These inputs are all ready pulled from the vertex_inputs
                    semantic = tidy_semantic(semantic, i.get('set'))
                    source = tidy_name(i.get('source'), prefix=self.id)
                    offset = int(i.get('offset', '0'))
                    old_input = self.inputs.get(semantic, None)
                    if old_input:
                        if old_input.source != source or old_input.offset != offset:
                            LOG.error('SEMANTIC "%s" used with different sources (%s:%d) != (%s:%d)',
                                      semantic, source, offset, old_input.source, old_input.offset)
                    else:
                        self.inputs[semantic] = Dae2Geometry.Input(semantic, source, offset)
                    if max_offset < offset:
                        max_offset = offset
                    sources.add(source)

        return max_offset, sources

    # pylint: disable=R0914
    def __init__(self, geometry_e, scale, library_geometries_e, name_map, geometry_names):
        self.name = None
        self.scale = scale
        self.sources = { }
        self.inputs = { }
        self.surfaces = { }
        self.meta = { }
        self.type = 'unknown'

        # Name...
        self.id = geometry_e.get('id', 'unknown')
        self.name = geometry_e.get('name', self.id)
        LOG.debug('GEOMETRY:%s', self.name)
        if self.name in geometry_names:
            LOG.warning('GEOMETRY name clash:%s:replacing with:%s', self.name, self.id)
            geometry_names[self.id] = self.name
            self.name = self.id
        else:
            geometry_names[self.name] = self.name

        name_map[self.id] = self.name

        # Mesh...
        mesh_e = geometry_e.find(tag('mesh'))
        if mesh_e is not None:
            self.type = 'mesh'
        else:
            # !!! Handle 'convex_mesh' correctly
            convex_mesh_e = geometry_e.find(tag('convex_mesh'))
            if convex_mesh_e is not None:
                reference_name = tidy_name(convex_mesh_e.get('convex_hull_of'))

                for reference_node_e in library_geometries_e.findall(tag('geometry')):
                    if reference_node_e.get('id') == reference_name:
                        mesh_e = reference_node_e.find(tag('mesh'))
                        self.type = 'convex_mesh'
                        break

                if mesh_e is None:
                    LOG.error('Unknown reference node:%s', reference_name)
                    return

            if geometry_e.find(tag('spline')):
                LOG.warning('Skipping spline based mesh:%s', self.name)
                self.type = 'spline'
                return

            if mesh_e is None:
                LOG.error('Unknown geometry type:%s', self.name)
                return


        # Sources...
        geometry_source_names = { }
        source_e = mesh_e.findall(tag('source'))
        for s in source_e:
            source_id = s.get('id', 'unknown')
            name = s.get('name', source_id)
            if name in geometry_source_names:
                LOG.warning('SOURCE name clash:%s:replacing with id:%s', name, source_id)
                geometry_source_names[source_id] = name
                name = source_id
            else:
                geometry_source_names[name] = name
            semantic = find_semantic(source_id, mesh_e)
            # We tidy the id after finding the semantic from the sources
            source_id = tidy_name(source_id, prefix=self.id)
            if semantic is not None:
                technique_e = s.find(tag('technique_common'))
                accessor_e = technique_e.find(tag('accessor'))
                stride = int(accessor_e.get('stride', '1'))
                array_e = s.find(tag('float_array'))
                count = int(array_e.get('count', '0'))
                if (0 < count) and (0 < stride):
                    values_text = array_e.text
                    values = [float(x) for x in values_text.split()]
                    if (semantic == 'POSITION') and (scale != 1.0):
                        values = [scale * x for x in values]

                    values = pack(values, stride)
                else:
                    values = None
                self.sources[source_id] = Dae2Geometry.Source(values, semantic, name, stride, count)
            else:
                LOG.warning('SOURCE (unusued):%s:semantic:%s', source_id, semantic)

        # Inputs...
        shared_sources = set()
        vertices_e = mesh_e.find(tag('vertices'))
        if vertices_e is not None:
            for i in vertices_e.findall(tag('input')):
                semantic = tidy_semantic(i.get('semantic'), i.get('set'))
                source = tidy_name(i.get('source'), prefix=self.id)
                # Offset 0 vertex inputs
                self.inputs[semantic] = Dae2Geometry.Input(semantic, source)
                shared_sources.add(source)

        # Mesh can contain:
        #
        # lines         - untested
        # linestrips
        # polygons      - supported (quads [replaced by triangles])
        # polylist      - supported
        # spline
        # triangles     - supported
        # trifans
        # tristrips

        # Triangles...
        for triangles_e in mesh_e.findall(tag('triangles')):
            max_offset, sources = self.add_input(triangles_e, shared_sources)
            if len(triangles_e) == 0:
                LOG.warning('GEOMETRY with no faces:%s', self.name)
                continue
            indices_per_vertex = max_offset + 1
            num_faces = int(triangles_e.get('count', '0'))
            material = triangles_e.get('material')

            indices_e = triangles_e.find(tag('p'))
            if indices_e is not None:
                indices = [int(x) for x in indices_e.text.split()]
                assert(3 * num_faces * indices_per_vertex == len(indices))
                indices = invert_indices(indices, indices_per_vertex, 3)
                self.surfaces[material] = Dae2Geometry.Surface(sources, indices, JsonAsset.SurfaceTriangles)

        # Polylist...
        for polylist_e in mesh_e.findall(tag('polylist')):
            max_offset, sources = self.add_input(polylist_e, shared_sources)
            if len(polylist_e) == 0:
                LOG.warning('GEOMETRY with no faces:%s', self.name)
                continue
            indices_per_vertex = max_offset + 1
            num_faces = int(polylist_e.get('count', '0'))
            material = polylist_e.get('material')

            indices_e = polylist_e.find(tag('p'))
            vertex_count_e = polylist_e.find(tag('vcount'))
            if vertex_count_e is not None:
                vertex_count = [int(x) for x in vertex_count_e.text.split()]
                assert(num_faces == len(vertex_count))

                indices = [int(x) for x in indices_e.text.split()]

                # Add everything as triangles.
                index = 0
                new_indices = [ ]
                for vcount in vertex_count:
                    face_indices = pack(indices[index:index + vcount * indices_per_vertex], indices_per_vertex)
                    index += vcount * indices_per_vertex
                    for t in range(2, vcount):
                        new_indices.append( (face_indices[0], face_indices[t-1], face_indices[t]) )
                self.surfaces[material] = Dae2Geometry.Surface(sources, new_indices, JsonAsset.SurfaceTriangles)

        # Lines...
        for lines_e in mesh_e.findall(tag('lines')):
            max_offset, sources = self.add_input(lines_e, shared_sources)
            if len(lines_e) == 0:
                LOG.warning('GEOMETRY with no faces:%s', self.name)
                continue
            indices_per_vertex = max_offset + 1
            num_faces = int(lines_e.get('count', '0'))
            material = lines_e.get('material')

            indices_e = lines_e.find(tag('p'))
            indices = [int(x) for x in indices_e.text.split()]
            indices = invert_indices(indices, indices_per_vertex, 2)
            self.surfaces[material] = Dae2Geometry.Surface(sources, indices, JsonAsset.SurfaceLines)

        # Polygons...
        for polygons_e in mesh_e.findall(tag('polygons')):
            max_offset, sources = self.add_input(polygons_e, shared_sources)
            if len(polygons_e) == 0:
                LOG.warning('GEOMETRY with no faces:%s', self.name)
                continue
            indices_per_vertex = max_offset + 1
            num_faces = int(polygons_e.get('count', '0'))
            material = polygons_e.get('material')

            indices = [ ]
            for p_e in polygons_e.findall(tag('p')):
                face_indices = pack([int(x) for x in p_e.text.split()], indices_per_vertex)
                vcount = len(face_indices)
                for t in range(2, vcount):
                    indices.append( (face_indices[0], face_indices[t-1], face_indices[t]) )

            if polygons_e.find(tag('ph')):
                LOG.warning('GEOMETRY using polygons with holes, please triangulate when exporting:%s.', self.name)

            if 0 < len(indices):
                self.surfaces[material] = Dae2Geometry.Surface(sources, indices, JsonAsset.SurfaceTriangles)
            else:
                LOG.warning('GEOMETRY without valid primitives:%s.', self.name)
    # pylint: enable=R0914

    # pylint: disable=R0914
    def process(self, definitions_asset, nodes, nvtristrip, materials, effects):
        # Look at the material to check for geometry requirements
        need_normals = False
        need_tangents = False
        generate_normals = False
        generate_tangents = False

        # Assumed to be a graphics geometry
        is_graphics_geometry = True

        if is_graphics_geometry:
            LOG.info('"%s" is assumed to be a graphics geometry. ' \
                     'Check referencing node for physics properties otherwise', self.name)
            self.meta['graphics'] = True

        for mat_name in self.surfaces.iterkeys():
            # Ok, we have a mat_name but this may need to be mapped if the node has an instanced material.
            # So we find the node referencing this geometry, and see if the material has a mapping on it.
            def _find_material_from_instance_on_node(n):
                for instance in n.instance_geometry:
                    if instance.geometry == self.id:
                        for surface, material in instance.materials.iteritems():
                            if surface == mat_name:
                                return material
                for child in n.children:
                    material = _find_material_from_instance_on_node(child)
                    if material is not None:
                        return material
                return None

            for _, node in nodes.iteritems():
                instance_mat_name = _find_material_from_instance_on_node(node)
                if instance_mat_name is not None:
                    LOG.debug('Using instance material:%s to %s', mat_name, instance_mat_name)
                    mat_name = instance_mat_name
                    break

            if mat_name is None:
                mat_name = 'default'

            effect_name = None
            meta = { }

            material = definitions_asset.retrieve_material(mat_name, False)
            if material is not None:
                effect_name = material.get('effect', None)
                if 'meta' in material:
                    meta.update(material['meta'])
            else:
                material = materials.get(mat_name, None)
                if material is not None:
                    effect_name = material.effect_name
                    # Dae2Material has no meta data, everything is on Dae2Effect
                else:
                    continue

            if effect_name is not None:
                effect = definitions_asset.retrieve_effect(effect_name)
                if effect is not None:
                    if 'meta' in effect:
                        meta.update(effect['meta'])
                else:
                    effect = effects.get(effect_name, None)
                    if effect is not None and effect.meta is not None:
                        meta.update(effect.meta)

            if meta.get('normals', False) is True:
                need_normals = True

            if meta.get('tangents', False) is True:
                need_tangents = True

            if meta.get('generate_normals', False) is True:
                generate_normals = True

            if meta.get('generate_tangents', False) is True:
                generate_tangents = True
                break

        if need_normals and 'NORMAL' not in self.inputs:
            generate_normals = True

        if need_tangents and 'TANGENT' not in self.inputs and 'BINORMAL' not in self.inputs:
            generate_tangents = True

        if generate_normals is False and generate_tangents is False and nvtristrip is None:
            return

        # Generate a single vertex pool.
        new_sources = { }
        old_semantics = { }
        old_offsets = { }

        has_uvs = False
        for semantic, input_stream in self.inputs.iteritems():
            new_sources[input_stream.source] = [ ]
            old_offsets[input_stream.source] = input_stream.offset
            old_semantics[semantic] = True
            if semantic == 'TEXCOORD' or semantic == 'TEXCOORD0':
                has_uvs = True

        if generate_tangents:
            if has_uvs is False:
                LOG.warning('Material "%s" requires tangents but geometry "%s" has no UVs', mat_name, self.name)
                return

        for mat_name, surface in self.surfaces.iteritems():
            if surface.type == JsonAsset.SurfaceTriangles:
                if generate_tangents:
                    LOG.info('Process:generate_tangents:geometry:%s:surface:%s', self.name, mat_name)
                elif generate_normals:
                    LOG.info('Process:generate_normals:geometry:%s:surface:%s', self.name, mat_name)
            elif surface.type == JsonAsset.SurfaceQuads:
                triangles = [ ]
                for (q0, q1, q2, q3) in surface.primitives:
                    triangles.append( ( q0, q1, q2) )
                    triangles.append( ( q0, q2, q3) )
                surface.primitives = triangles
                surface.type = JsonAsset.SurfaceTriangles
                LOG.info('Triangulated geometry:%s:surface:%s', self.name, mat_name)
                if generate_tangents:
                    LOG.info('Process:generate_tangents:geometry:%s:surface:%s', self.name, mat_name)
                elif generate_normals:
                    LOG.info('Process:generate_normals:geometry:%s:surface:%s', self.name, mat_name)
            else:
                return

        # For each surface in the geometry...
        new_surfaces = { }

        index = 0
        for mat_name, surface in self.surfaces.iteritems():
            start_index = index
            surface_sources = surface.sources

            # For each primitive within the surface...
            for primitive in surface.primitives:
                index += 1

                if isinstance(primitive[0], (tuple, list)):
                    # For each input source and input offset...
                    for source, offset in old_offsets.iteritems():
                        new_source = new_sources[source]
                        if source in surface_sources:
                            source_values = self.sources[source].values
                            # For each vertex in the primitive (triangle or quad)...
                            for vertex in primitive:
                                new_source.append( source_values[vertex[offset]] )
                        else:
                            zero = self.sources[source].zero_value
                            for vertex in primitive:
                                new_source.append(zero)
                else:
                    # For each input source and input offset...
                    for source in old_offsets.iterkeys():
                        new_source = new_sources[source]
                        if source in surface_sources:
                            source_values = self.sources[source].values
                            # For each vertex in the primitive (triangle or quad)...
                            for vertex in primitive:
                                new_source.append( source_values[vertex] )
                        else:
                            zero = self.sources[source].zero_value
                            for vertex in primitive:
                                new_source.append(zero)

            end_index = index
            new_surfaces[mat_name] = (start_index, end_index)

        mesh = Mesh()
        for semantic, input_stream in self.inputs.iteritems():
            mesh.set_values(new_sources[input_stream.source], semantic)

        mesh.primitives = [ (i, i + 1, i + 2) for i in range(0, index * 3, 3) ]
        #mesh.mirror_in('z')

        if generate_normals:
            mesh.generate_normals()
            mesh.smooth_normals()
            old_semantics['NORMAL'] = True

        if generate_tangents:
            mesh.generate_tangents()
            mesh.normalize_tangents()
            mesh.smooth_tangents()
            mesh.generate_normals_from_tangents()
            mesh.smooth_normals()
            old_semantics['TANGENT'] = True
            old_semantics['BINORMAL'] = True

        def compact_stream(values, semantic):
            """Generate a new value and index stream remapping and removing duplicate elements."""
            new_values = [ ]
            new_values_hash = { }
            new_index = [ ]
            for v in values:
                if v in new_values_hash:
                    new_index.append(new_values_hash[v])
                else:
                    i = len(new_values)
                    new_index.append(i)
                    new_values.append(v)
                    new_values_hash[v] = i

            LOG.info('%s stream compacted from %i to %i elements', semantic, len(values), len(new_values))
            return (new_values, new_index)

        # !!! This should be updated to find index buffers that are similar rather than identical.
        new_indexes = [ ]
        new_offsets = { }
        for semantic in old_semantics.iterkeys():
            values = mesh.get_values(semantic)
            (new_values, new_values_index) = compact_stream(values, semantic)
            mesh.set_values(new_values, semantic)
            for i, indexes in enumerate(new_indexes):
                if indexes == new_values_index:
                    new_offsets[semantic] = i
                    break
            else:
                new_offsets[semantic] = len(new_indexes)
                new_indexes.append(new_values_index)

        indexes = zip(*new_indexes)

        # Use NVTriStrip to generate a vertex cache aware triangle list
        if nvtristrip is not None:
            for (start_index, end_index) in new_surfaces.itervalues():
                reverse_map = {}
                indexes_map = {}
                num_vertices = 0
                for n in xrange(start_index * 3, end_index * 3):
                    index = indexes[n]
                    if index not in indexes_map:
                        indexes_map[index] = num_vertices
                        reverse_map[num_vertices] = index
                        num_vertices += 1
                #LOG.info(num_vertices)

                if num_vertices < 65536:
                    #LOG.info(indexes)
                    try:
                        nvtristrip_proc = subprocess.Popen([nvtristrip],
                                                           stdin = subprocess.PIPE,
                                                           stdout = subprocess.PIPE)

                        stdin_write = nvtristrip_proc.stdin.write
                        for n in xrange(start_index * 3, end_index * 3):
                            index = indexes[n]
                            value = indexes_map[index]
                            stdin_write(str(value) + "\n")
                        stdin_write("-1\n")
                        stdin_write = None
                        indexes_map = None

                        stdout_readline = nvtristrip_proc.stdout.readline
                        try:
                            num_groups = int(stdout_readline())
                            group_type = int(stdout_readline())
                            num_indexes = int(stdout_readline())
                            if num_groups != 1 or group_type != 0 or num_indexes != (end_index - start_index) * 3:
                                LOG.warning("NvTriStripper failed: %d groups, type %d, %d indexes.",
                                            num_groups, group_type, num_indexes)
                            else:
                                n = start_index * 3
                                for value in stdout_readline().split():
                                    value = int(value)
                                    indexes[n] = reverse_map[value]
                                    n += 1
                        except ValueError as e:
                            error_string = str(e).split("'")
                            if 1 < len(error_string):
                                error_string = error_string[1]
                            else:
                                error_string = str(e)
                            LOG.warning("NvTriStripper failed: %s", error_string)
                        stdout_readline = None
                        nvtristrip_proc = None
                        #LOG.info(indexes)

                    except OSError as e:
                        LOG.warning("NvTriStripper failed: " + str(e))
                else:
                    LOG.warning("Too many vertices to use NvTriStrip: %d", num_vertices)
                indexes_map = None
                reverse_map = None

        primitives = [ (indexes[i], indexes[i + 1], indexes[i + 2]) for i in xrange(0, len(indexes), 3) ]

        # Fix up the surfaces...
        for mat_name, (start_index, end_index) in new_surfaces.iteritems():
            self.surfaces[mat_name].primitives = primitives[start_index:end_index]

        # Fix up the inputs...
        for semantic, input_stream in self.inputs.iteritems():
            input_stream.offset = new_offsets[semantic]

        # Fix up the sources...
        for _, source in self.sources.iteritems():
            source.values = mesh.get_values(source.semantic)

        if generate_normals:
            self.inputs['NORMAL'] = Dae2Geometry.Input('NORMAL', 'normals', new_offsets['NORMAL'])
            self.sources['normals'] = Dae2Geometry.Source(mesh.normals, 'NORMAL', 'normals', 3, len(mesh.normals))

        if generate_tangents:
            self.inputs['BINORMAL'] = Dae2Geometry.Input('BINORMAL', 'binormals', new_offsets['BINORMAL'])
            self.inputs['TANGENT'] = Dae2Geometry.Input('TANGENT', 'tangents', new_offsets['TANGENT'])
            self.sources['binormals'] = Dae2Geometry.Source(mesh.binormals,
                                                            'BINORMAL',
                                                            'binormals',
                                                            3,
                                                            len(mesh.binormals))
            self.sources['tangents'] = Dae2Geometry.Source(mesh.tangents,
                                                           'TANGENT',
                                                           'tangents',
                                                           3,
                                                           len(mesh.tangents))
   # pylint: enable=R0914

    def attach(self, json_asset):
        json_asset.attach_shape(self.name)
        json_asset.attach_meta(self.meta, self.name)
        for surface_name, surface in self.surfaces.iteritems():
            json_asset.attach_surface(surface.primitives, surface.type, self.name, surface_name)
        for semantic, i in self.inputs.iteritems():
            source = self.sources[i.source]
            if semantic.startswith('TEXCOORD'):
                mesh = Mesh()
                mesh.uvs[0] = source.values
                mesh.invert_v_texture_map()
                source.values = mesh.uvs[0]
                mesh = None
            json_asset.attach_stream(source.values, self.name, source.name, semantic, source.stride, i.offset)

    def __repr__(self):
        return 'Dae2Geometry<sources:%s:inputs:%s>' % (self.sources, self.inputs)

class Dae2Effect(object):
    def __init__(self, effect_e, url_handler, name_map, effect_names):
        self.shader_path = None
        self.type = None
        self.params = { }
        self.meta = None

        # Name...
        self.id = effect_e.get('id', 'unknown')
        self.name = effect_e.get('name', self.id)
        if self.name in effect_names:
            LOG.warning('EFFECT name clash:%s:replacing with:%s', self.name, self.id)
            effect_names[self.id] = self.name
            self.name = self.id
        else:
            effect_names[self.name] = self.name

        name_map[self.id] = self.name

        for extra_e in effect_e.findall(tag('extra')):
            extra_type = extra_e.get('type')
            if extra_type is not None and extra_type == 'import':
                technique_e = extra_e.find(tag('technique'))
                if technique_e is not None:
                    technique_profile =  technique_e.get('profile')
                    if technique_profile is not None and (technique_profile == 'NV_import' or \
                                                          technique_profile == 'NVIDIA_FXCOMPOSER'):
                        import_e = technique_e.find(tag('import'))
                        if import_e is not None:
                            profile = import_e.get('profile')
                            if profile is not None and profile == 'cgfx':
                                url = import_e.get('url')
                                self.shader_path = url_handler.tidy(url)

        cg_profile = False
        profile_e = effect_e.find(tag('profile_COMMON'))
        if profile_e is None:
            for profile_CG_e in effect_e.findall(tag('profile_CG')):
                platform = profile_CG_e.get('platform')
                if platform is None or platform == 'PC-OGL':
                    cg_profile = True
                    profile_e = profile_CG_e
                    include_e = profile_CG_e.find(tag('include'))
                    if include_e is not None:
                        url = include_e.get('url')
                        if url is not None and 'cgfx' in url:
                            self.shader_path = url_handler.tidy(url)

        if cg_profile:
            self.type = 'cgfx'

        else:
            technique_e = profile_e.find(tag('technique'))
            if technique_e is None:
                return

            type_e = technique_e.getchildren()
            if type_e is None or len(type_e) == 0:
                return
            self.type = untag(type_e[0].tag)

            def _add_texture(param_name, texture_e):
                texture_name = None
                sampler_name = texture_e.get('texture')
                if sampler_name is not None:
                    sampler_e = find_new_param(profile_e, sampler_name)
                    if sampler_e is not None:
                        sampler_type_e = sampler_e[0]
                        if sampler_type_e is not None:
                            source_e = sampler_type_e.find(tag('source'))
                            if source_e is not None:
                                surface_param_e = find_new_param(profile_e, source_e.text)
                                if surface_param_e is not None:
                                    surface_e = surface_param_e.find(tag('surface'))
                                    if surface_e is not None:
                                        image_e = surface_e.find(tag('init_from'))
                                        if image_e is not None:
                                            texture_name = image_e.text
                    else:
                        texture_name = sampler_name

                if texture_name is None:
                    self.params[param_name] = 'null'
                else:
                    self.params[param_name] = find_name(name_map, texture_name)

            for param_e in type_e[0].getchildren():
                param_name = untag(param_e.tag)
                texture_e = param_e.find(tag('texture'))
                if texture_e is not None:
                    _add_texture(param_name, texture_e)
                else:
                    for value_e in param_e.getchildren():
                        value_type = untag(value_e.tag)
                        value_text = value_e.text
                        if value_type == 'param':
                            param_ref = value_e.get('ref')
                            param_ref_e = find_new_param(profile_e, param_ref)
                            if param_ref_e is not None:
                                for ref_value_e in param_ref_e.getchildren():
                                    value_type = untag(ref_value_e.tag)
                                    value_text = ref_value_e.text
                        if value_type == 'color':
                            color = [ float(x) for x in value_text.split() ]
                            if param_name == 'transparent':
                                mode = param_e.get('opaque') or 'A_ONE'
                                if mode == 'A_ONE':
                                    color[0] = color[1] = color[2] = color[3]
                                elif mode == 'A_ZERO':
                                    color[0] = color[1] = color[2] = 1.0 - color[3]
                                elif mode == 'RGB_ZERO':
                                    color[0] = 1.0 - color[0]
                                    color[1] = 1.0 - color[1]
                                    color[2] = 1.0 - color[2]
                            self.params[param_name] = color
                        else:
                            self.params[param_name] = tidy_value(value_text, value_type)

            # Process extensions
            extra_e = technique_e.find(tag('extra'))
            if extra_e is not None:
                extra_techniques = extra_e.findall(tag('technique'))
                if extra_techniques:
                    for extra_technique_e in extra_techniques:
                        bump_e = extra_technique_e.find(tag('bump'))
                        if bump_e is not None:
                            texture_e = bump_e.find(tag('texture'))
                            if texture_e is not None:
                                _add_texture('bump', texture_e)

            tint_color_e = find_new_param(profile_e, '_TintColor')
            if tint_color_e is not None:
                value_e = tint_color_e.find(tag('float4'))
                if value_e is not None:
                    value_text = value_e.text
                    color = [ float(x) for x in value_text.split() ]
                    self.params['TintColor'] = color

            # Convert COLLADA effects to Turbulenz Effects
            if self.type in ['blinn', 'phong', 'lambert']:
                self._patch_type()

    def _patch_type(self):
        if 'TintColor' in self.params:
            material_color = self.params['TintColor']
            del self.params['TintColor']
        else:
            material_color = [1, 1, 1, 1]
        alpha = material_color[3]

        if 'ambient' in self.params:
            del self.params['ambient']

        if 'diffuse' in self.params:
            diffuse = self.params['diffuse']
            if isinstance(diffuse, list):
                material_color = diffuse
                del self.params['diffuse']

        if 'emission' in self.params:
            emission = self.params['emission']
            if not isinstance(emission, list):
                if 'diffuse' in self.params:
                    self.params['light_map'] = emission
                else:
                    self.params['glow_map'] = emission
            del self.params['emission']

        if 'bump' in self.params:
            bump = self.params['bump']
            if not isinstance(bump, list):
                self.params['normal_map'] = bump
            del self.params['bump']

        if 'specular' in self.params:
            specular = self.params['specular']
            if not isinstance(specular, list):
                self.params['specular_map'] = specular
            del self.params['specular']

        if 'reflective' in self.params:
            reflective = self.params['reflective']
            if not isinstance(reflective, list):
                self.params['env_map'] = reflective
            del self.params['reflective']

        if 'transparency' in self.params:
            transparency = self.params['transparency']
            if transparency == 0.0:
                # This is a usual bug on older exporters, it means opaque
                if 'transparent' in self.params:
                    del self.params['transparent']
            else:
                alpha *= transparency
            del self.params['transparency']

        if 'transparent' in self.params:
            transparent = self.params['transparent']
            if not isinstance(transparent, list):
                if transparent == self.params.get('diffuse', None):
                    alpha = 0.9999
            else:
                transparent = min(transparent)
                alpha = min(alpha, transparent)
            del self.params['transparent']

        meta = { }

        if alpha < 1.0:
            self.type = 'blend'
            if alpha > 0.99:
                alpha = 1
            material_color[3] = alpha
            meta['transparent'] = True
            if 'diffuse' not in self.params:
                self.params['diffuse'] = 'white'
        elif 'light_map' in self.params:
            self.type = 'lightmap'
        elif 'normal_map' in self.params:
            self.type = 'normalmap'
            if 'specular_map' in self.params:
                self.type += '_specularmap'
            if 'glow_map' in self.params:
                self.type += '_glowmap'
            meta['normals'] = True
            meta['tangents'] = True
        elif 'glow_map' in self.params:
            self.type = 'glowmap'
        elif 'diffuse' not in self.params:
            self.type = 'constant'
            meta['normals'] = True
        else:
            meta['normals'] = True

        if min(material_color) < 1.0:
            self.params['materialColor'] = material_color

        if meta:
            if self.meta is None:
                self.meta = meta
            else:
                self.meta.update(meta)

    def attach(self, json_asset, definitions_asset):

        def _attach_effect(effect_name):
            effect = definitions_asset.retrieve_effect(effect_name)
            if effect is not None:
                json_asset.attach_effect(self.name, raw=effect)
                return True
            return False

        if definitions_asset is not None:
            if _attach_effect(self.name) or _attach_effect(self.name.lower()):
                return

        # If we did not find an effect in the definitions_asset then we need to add the effect from
        # the Collada asset.
        json_asset.attach_effect(self.name, self.type, self.params, self.shader_path, self.meta)

class Dae2Material(object):
    def __init__(self, material_e, name_map):
        self.effect_name = None
        self.technique_name = None
        self.params = { }

        # Name...
        self.id = material_e.get('id', 'unknown')
        self.name = material_e.get('name', self.id)
        name_map[self.id] = self.name

        # Effect...
        effect_e = material_e.find(tag('instance_effect'))
        self.effect_name = tidy_name(effect_e.get('url'))

        # Technique...
        for technique_hint_e in effect_e.findall(tag('technique_hint')):
            platform = technique_hint_e.get('platform')
            if platform is None or platform == 'PC-OGL':
                self.technique_name = technique_hint_e.get('ref')
                if self.technique_name is not None:
                    break

        # Params...
        for param_e in effect_e.findall(tag('setparam')):
            param_name = param_e.get('ref')
            for value_e in param_e.getchildren():
                value_type = untag(value_e.tag)
                if value_type.startswith('sampler'):
                    texture_name = 'null'
                    source_e = value_e.find(tag('source'))
                    if source_e is not None:
                        surface_param_e = find_set_param(effect_e, source_e.text)
                        if surface_param_e is not None:
                            surface_e = surface_param_e.find(tag('surface'))
                            if surface_e is not None:
                                texture_e = surface_e.find(tag('init_from'))
                                if texture_e is not None:
                                    texture_name = texture_e.text
                    self.params[param_name] = find_name(name_map, texture_name)
                elif value_type != 'surface':
                    value_text = value_e.text
                    self.params[param_name] = tidy_value(value_text, value_type)

    def attach(self, json_asset, definitions_asset, name_map):

        def _attach_materials(mat_name):
            # This attaches any skins and *additional* materials used by the skins.
            attach_skins_and_materials(json_asset, definitions_asset, mat_name, False)
            # This attaches the current material.
            material = definitions_asset.retrieve_material(mat_name, False)
            if material is not None:
                json_asset.attach_material(self.name, raw=material)
                return True
            return False

        # !!! Consider adding options to support Overload and Fallback assets, then the order of assets would be:
        # 1. Overload material
        # 2. Original material
        # 3. Fallback material
        if definitions_asset is not None:
            if _attach_materials(self.name) or _attach_materials(self.name.lower()):
                return

        # If we did not find a material in the definitions_asset then we need to add the material from
        # the Collada asset.
        effect_name = find_name(name_map, self.effect_name)
        if len(self.params) == 0:
            json_asset.attach_material(self.name, effect_name, self.technique_name)
        else:
            json_asset.attach_material(self.name, effect_name, self.technique_name, self.params)

class Dae2Image(object):
    def __init__(self, image_e, url_handler, name_map):
        self.image_path = None

        self.id = image_e.get('id', 'unknown')
        self.name = image_e.get('name', self.id)
        name_map[self.id] = self.name

        from_e = image_e.find(tag('init_from'))
        if from_e is not None and from_e.text is not None:
            self.image_path = url_handler.tidy(from_e.text)

    def attach(self, json_asset):
        json_asset.attach_image(self.image_path, self.name)

class Dae2Light(object):
    def __init__(self, light_e, name_map, light_names):
        self.params = { }

        # Name...
        self.id = light_e.get('id', 'unknown')
        self.name = light_e.get('name', self.id)
        if self.name in light_names:
            LOG.warning('LIGHT name clash:%s:replacing with:%s', self.name, self.id)
            light_names[self.id] = self.name
            self.name = self.id
        else:
            light_names[self.name] = self.name

        name_map[self.id] = self.name

        common_e = light_e.find(tag('technique_common'))
        if common_e is not None:
            type_e = common_e[0]
            self.params['type'] = untag(type_e.tag)

            for param_e in type_e:
                param_name = untag(param_e.tag)
                if param_name == 'color':
                    self.params[param_name] = [float(x) for x in param_e.text.split()]
                else:
                    self.params[param_name] = float(param_e.text)

    def attach(self, json_asset, definitions_asset):

        def _attach_light(light_name):
            light = definitions_asset.retrieve_light(light_name)
            if light is not None:
                json_asset.attach_light(light_name, raw=light)
                if 'material' in light:
                    mat_name = light['material']
                    material = definitions_asset.retrieve_material(mat_name, False)
                    if material is not None:
                        json_asset.attach_material(mat_name, raw=material)
                return True
            return False

        if definitions_asset is not None:
            if _attach_light(self.name) or _attach_light(self.name.lower()):
                return

        # If we did not find a light in the definitions_asset then we need to add the light from
        # the Collada asset.
        constant_atten = 1
        linear_atten = 0
        quadratic_atten = 0
        if 'constant_attenuation' in self.params:
            constant_atten = self.params['constant_attenuation']
            del self.params['constant_attenuation']
        if 'linear_attenuation' in self.params:
            linear_atten = self.params['linear_attenuation']
            del self.params['linear_attenuation']
        if 'quadratic_attenuation' in self.params:
            quadratic_atten = self.params['quadratic_attenuation']
            del self.params['quadratic_attenuation']

        # generate a radius for the light
        # solve quadratic equation for attenuation 1/100
        # att = 1 / (constant_atten + (range * linear_atten) + (range * range * quadratic_atten))
        if quadratic_atten > 0:
            c = (constant_atten - 100)
            b = linear_atten
            a = quadratic_atten
            q = math.sqrt((b * b) - (4 * a * c))
            self.params['radius'] = max( (-b + q) / (2 * a),  (-b - q) / (2 * a))
        elif linear_atten > 0:
            self.params['radius'] = (100 - constant_atten) / linear_atten
        else:
            self.params['global'] = True

        json_asset.attach_light(self.name, self.params)

class Dae2Node(object):

    class InstanceGeometry(object):
        def __init__(self, instance_e):
            self.geometry = tidy_name(instance_e.get('url'))
            self.materials = { }
            bind_e = instance_e.find(tag('bind_material'))
            found_material = False
            if bind_e is not None:
                technique_e = bind_e.find(tag('technique_common'))
                if technique_e is not None:
                    for material_e in technique_e.findall(tag('instance_material')):
                        self.materials[material_e.get('symbol')] = tidy_name(material_e.get('target'))
                        found_material = True
            if not found_material:
                LOG.warning('INSTANCE_GEOMETRY with no material:url:%s:using:default', self.geometry)
                self.materials['default'] = 'default'

        def attach(self, json_asset, name_map, node_name=None):
            for surface, material in self.materials.iteritems():
                geom_name = find_name(name_map, self.geometry)
                mat_name = find_name(name_map, material)

                if len(self.materials) > 1:
                    surface_name = geom_name + '-' + mat_name
                else:
                    surface_name = geom_name

                json_asset.attach_node_shape_instance(node_name, surface_name, geom_name, mat_name, surface)

    class InstanceController(object):

        class Skin(object):
            def __init__(self, skin_e, scale, geometry):
                self.sources = { }
                self.inv_ltms = { }
                self.joint_names = [ ]
                self.joint_parents = { }
                self.joint_bind_poses = { }
                self.geometry = geometry
                self.scale = scale

                bind_matrix_e = skin_e.find(tag('bind_shape_matrix'))
                if bind_matrix_e is not None:
                    transpose = vmath.m44transpose([float(x) for x in bind_matrix_e.text.split()])
                    self.bind_matrix = vmath.m43from_m44(transpose)
                    self.bind_matrix = vmath.m43setpos(self.bind_matrix,
                                                       vmath.v3muls(vmath.m43pos(self.bind_matrix),
                                                       self.scale))
                else:
                    self.bind_matrix = vmath.M43IDENTITY

                source_e = skin_e.findall(tag('source'))
                for s in source_e:
                    technique_e = s.find(tag('technique_common'))
                    accessor_e = technique_e.find(tag('accessor'))
                    param_e = accessor_e.find(tag('param'))
                    param_name = param_e.get('name')
                    param_type = param_e.get('type')
                    if param_type.lower() == 'name' or param_type == 'IDREF':
                        sids = True
                        array_e = s.find(tag('Name_array'))
                        if array_e is None:
                            array_e = s.find(tag('IDREF_array'))
                            sids = False
                        count = int(array_e.get('count', '0'))
                        if (0 < count):
                            values_text = array_e.text
                            self.sources[s.get('id')] = { 'name': param_name,
                                                          'values': values_text.split(),
                                                          'sids': sids }
                    elif param_type == 'float':
                        array_e = s.find(tag('float_array'))
                        count = int(array_e.get('count', '0'))
                        if (0 < count):
                            values_text = array_e.text
                            values = [float(x) for x in values_text.split()]
                            self.sources[s.get('id')] = { 'name': param_name, 'values': values }
                    elif param_type == 'float4x4':
                        array_e = s.find(tag('float_array'))
                        count = int(array_e.get('count', '0'))
                        if (0 < count):
                            values_text = array_e.text
                            float_values = [float(x) for x in values_text.split()]
                            values = [ ]
                            for i in range(0, len(float_values), 16):
                                matrix = vmath.m44transpose(float_values[i:i+16])
                                values.append(vmath.m43from_m44(matrix))
                            self.sources[s.get('id')] = { 'name': param_name, 'values': values }
                    else:
                        LOG.warning('SKIN with unknown param type:%s:ignoring', param_type)
                joints_e = skin_e.find(tag('joints'))
                inputs = joints_e.findall(tag('input'))
                for i in inputs:
                    semantic = i.get('semantic')
                    if semantic == 'JOINT':
                        self.joint_input = tidy_name(i.get('source'))
                    elif semantic == 'INV_BIND_MATRIX':
                        self.inv_ltm_input = tidy_name(i.get('source'))

                vertex_weights_e = skin_e.find(tag('vertex_weights'))
                inputs = vertex_weights_e.findall(tag('input'))
                for i in inputs:
                    semantic = i.get('semantic')
                    if semantic == 'JOINT':
                        self.indices_input = tidy_name(i.get('source'))
                        self.indices_offset = int(i.get('offset'))
                    elif semantic == 'WEIGHT':
                        self.weights_input = tidy_name(i.get('source'))
                        self.weights_offset = int(i.get('offset'))
                weights_per_vertex_e = vertex_weights_e.find(tag('vcount'))
                self.weights_per_vertex = [ int(x) for x in weights_per_vertex_e.text.split() ]
                skin_data_indices_e = vertex_weights_e.find(tag('v'))
                self.skin_data_indices = [ int(x) for x in skin_data_indices_e.text.split() ]

            def process(self, nodes):
                # Build a skeleton for the skinned mesh
                joint_names = self.sources[self.joint_input]['values']
                sid_joints = self.sources[self.joint_input]['sids']
                hierarchy = build_joint_hierarchy(joint_names, nodes, sid_joints)
                for j in hierarchy:
                    node = j['node']
                    parent_index = j['parent']
                    original_joint_index = j['orig_index']
                    if original_joint_index is not -1:
                        inv_bind_ltm = self.sources[self.inv_ltm_input]['values'][original_joint_index]

                        bind_ltm = vmath.m43inverse(inv_bind_ltm)
                        bind_ltm = vmath.m43setpos(bind_ltm,
                                                   vmath.v3muls(vmath.m43pos(bind_ltm),
                                                   self.scale))

                        inv_bind_ltm = vmath.m43setpos(inv_bind_ltm,
                                                       vmath.v3muls(vmath.m43pos(inv_bind_ltm),
                                                       self.scale))
                        inv_bind_ltm = vmath.m43mul(self.bind_matrix, inv_bind_ltm)

                        self.joint_names.append(node.name)
                        self.joint_parents[node.name] = parent_index
                        self.joint_bind_poses[node.name] = bind_ltm
                        self.inv_ltms[node.name] = inv_bind_ltm
                    else:
                        self.joint_names.append(node.name)
                        self.joint_parents[node.name] = parent_index
                        self.joint_bind_poses[node.name] = vmath.M43IDENTITY
                        self.inv_ltms[node.name] = vmath.M43IDENTITY

                # Build a skinning index mapping to the new joints
                skin_index_map = [ -1 ] * len(joint_names)
                for i, j in enumerate(hierarchy):
                    original_joint_index = j['orig_index']
                    if original_joint_index is not -1:
                        skin_index_map[original_joint_index] = i

                # Attach skinning data to the geometry
                g_inputs = self.geometry.inputs
                g_sources = self.geometry.sources
                positions_offset = g_inputs['POSITION'].offset
                count = len(g_sources[g_inputs['POSITION'].source].values)
                g_inputs['BLENDINDICES'] = Dae2Geometry.Input('BLENDINDICES', self.indices_input, positions_offset)
                g_inputs['BLENDWEIGHT'] = Dae2Geometry.Input('BLENDWEIGHT', self.weights_input, positions_offset)

                weight_source_values = self.sources[self.weights_input]['values']
                index_offset = 0
                index_data = []
                weight_data = []
                for wc in self.weights_per_vertex:
                    weights_list = []
                    for i in range(0, wc):
                        index = self.skin_data_indices[index_offset + self.indices_offset]
                        # remap the index
                        index = skin_index_map[index]
                        weight_index = self.skin_data_indices[index_offset + self.weights_offset]
                        weight = weight_source_values[weight_index]
                        index_offset += 2
                        weights_list.append((weight, index))
                    weights_list = sorted(weights_list, key=lambda weight: weight[0], reverse=True)
                    weight_scale = 1
                    if (len(weights_list) > 4):
                        weight_sum = weights_list[0][0] + weights_list[1][0] + weights_list[2][0] + weights_list[3][0]
                        weight_scale = 1 / weight_sum
                    for i in range(0, 4):
                        if i < len(weights_list):
                            (weight, index) = weights_list[i]
                            index_data.append(index)
                            weight_data.append(weight * weight_scale)
                        else:
                            index_data.append(0)
                            weight_data.append(0)

                g_sources[self.indices_input] = Dae2Geometry.Source(pack(index_data, 4), 'BLENDINDICES',
                                                                    'skin-indices', 1, count)
                g_sources[self.weights_input] = Dae2Geometry.Source(pack(weight_data, 4), 'BLENDWEIGHT',
                                                                    'skin-weights', 1, count)

                # update set of sources referenced by each surface
                for surface in self.geometry.surfaces.itervalues():
                    surface.sources.add(self.indices_input)
                    surface.sources.add(self.weights_input)

        def __init__(self, instance_controller_e, scale, controllers_e, child_name, geometries):
            self.skeleton = None
            self.skin = None
            self.geometry = None
            self.materials = { }

            skeleton_e = instance_controller_e.find(tag('skeleton'))
            if skeleton_e is not None:
                self.skeleton_name = tidy_name(skeleton_e.text)

            controller_name = tidy_name(instance_controller_e.get('url'))
            controller_e = find_controller(controller_name, controllers_e)
            if controller_e is not None:
                skin_e = controller_e.find(tag('skin'))
                if skin_e is not None:
                    geometry_id = tidy_name(skin_e.get('source'))
                    if geometry_id in geometries:
                        self.geometry = geometry_id
                        self.skin = Dae2Node.InstanceController.Skin(skin_e, scale, geometries[self.geometry])

            found_material = False
            bind_e = instance_controller_e.find(tag('bind_material'))
            if bind_e is not None:
                technique_e = bind_e.find(tag('technique_common'))
                if technique_e is not None:
                    for material_e in technique_e.findall(tag('instance_material')):
                        self.materials[material_e.get('symbol')] = tidy_name(material_e.get('target'))
                        found_material = True
            if not found_material:
                LOG.warning('INSTANCE_GEOMETRY with no material:url:%s:using:default', self.geometry)
                self.materials['default'] = 'default'

            self.child_name = child_name

        def process(self, nodes):
            if self.skin:
                self.skin.process(nodes)

                # Process a skeleton if we have a skin, note if this is moved to process we should always extract the
                # joint names
                joint_names = [ ]
                joint_parents = [ ]
                joint_bind_poses = [ ]
                inv_ltms = [ ]
                for j in self.skin.joint_names:
                    joint_names.append(j)
                    joint_parents.append(self.skin.joint_parents[j])
                    joint_bind_poses.append(self.skin.joint_bind_poses[j])
                    inv_ltms.append(self.skin.inv_ltms[j])
                self.skeleton = {
                    'numNodes': len(joint_names),
                    'names': joint_names,
                    'parents': joint_parents,
                    'bindPoses': joint_bind_poses,
                    'invBoneLTMs': inv_ltms }

        def attach(self, json_asset, name_map, parent_node_name=None):
            if self.geometry is None:
                LOG.warning('Skipping INSTANCE_CONTROLLER with no geometry attached to %s', parent_node_name)
                return
            if self.child_name is None:
                node_name = parent_node_name
            else:
                node_name = NodeName(self.child_name).add_parent_node(parent_node_name)

            for surface, material in self.materials.iteritems():
                geom_name = find_name(name_map, self.geometry)
                mat_name = find_name(name_map, material)

                if len(self.materials) > 1:
                    surface_name = geom_name + '-' + mat_name
                else:
                    surface_name = geom_name

                json_asset.attach_node_shape_instance(node_name, surface_name, geom_name, mat_name, surface)

                instance_attributes = { }
                node_attributes = { }

                if self.skin is not None:
                    instance_attributes['skinning'] = True
                    node_attributes['dynamic'] = True

                skeleton_name = self.geometry + '-skeleton'
                if hasattr(self , 'skeleton_name'):
                    skeleton_name = self.skeleton_name
                if skeleton_name is not None:
                    json_asset.attach_geometry_skeleton(geom_name, skeleton_name)
                    json_asset.attach_skeleton(self.skeleton, skeleton_name)

                json_asset.attach_shape_instance_attributes(node_name, surface_name, instance_attributes)
                json_asset.attach_node_attributes(node_name, node_attributes)

    def _build_node_path(self):
        path = NodeName(self.name)
        parents = []
        parent = self.parent
        while parent:
            parents.append(parent.name)
            parent = parent.parent
        if parents:
            parents.reverse()
            path.add_parents(parents)
        return path

# pylint: disable=R0913,R0914
    def __init__(self, node_e, global_scale, parent_node, parent_matrix, parent_prefix, controllers_e, collada_e,
                 name_map, node_names, node_map, geometries):
        self.matrix = None

        # !!! Put these in a dictionary??
        self.lights = [ ]
        self.cameras = [ ]
        self.references = [ ]
        self.instance_geometry = [ ]
        self.instance_controller = [ ]
        self.parent = parent_node
        self.children = [ ]
        self.animated = False

        self.element = node_e
        self.id = node_e.get('id', 'unnamed')
        self.sid = node_e.get('sid', None)
        node_name = node_e.get('name', self.id)
        if parent_prefix is not None:
            node_name = parent_prefix + '-' + node_name
        self.name = node_name

        path = self._build_node_path()
        path_str = str(path)
        if path_str in node_names:
            self.name += self.id
            path.name = self.name
            LOG.warning('NODE name clash:%s:replacing with:%s', path_str, str(path))
            path_str = str(path)
        self.path = path

        name_map[self.id] = self.name
        node_names[path_str] = self
        node_map[self.id] = self

        matrix = vmath.M44IDENTITY
        if parent_matrix is not None:
            matrix = parent_matrix # Make sure we get a copy

        for node_param_e in node_e:
            child_type = untag(node_param_e.tag)
            if child_type == 'translate':
                offset = [ float(x) for x in node_param_e.text.split() ]
                translate_matrix = vmath.m43(1.0, 0.0, 0.0,
                                             0.0, 1.0, 0.0,
                                             0.0, 0.0, 1.0,
                                             offset[0], offset[1], offset[2])
                matrix = vmath.m43mulm44(translate_matrix, matrix)

            elif child_type == 'rotate':
                rotate = [ float(x) for x in node_param_e.text.split() ]
                if rotate[3] != 0.0:
                    angle = rotate[3] / 180.0 * math.pi
                    if rotate[0] == 1.0 and rotate[1] == 0.0 and rotate[2] == 0.0:
                        c = math.cos(angle)
                        s = math.sin(angle)
                        rotate_matrix = vmath.m33(1.0, 0.0, 0.0,
                                                  0.0,   c,   s,
                                                  0.0,  -s,   c)
                    elif rotate[0] == 0.0 and rotate[1] == 1.0 and rotate[2] == 0.0:
                        c = math.cos(angle)
                        s = math.sin(angle)
                        rotate_matrix = vmath.m33(  c, 0.0,  -s,
                                                  0.0, 1.0, 0.0,
                                                    s, 0.0,   c)
                    elif rotate[0] == 0.0 and rotate[1] == 0.0 and rotate[2] == 1.0:
                        c = math.cos(angle)
                        s = math.sin(angle)
                        rotate_matrix = vmath.m33(  c,   s, 0.0,
                                                   -s,   c, 0.0,
                                                  0.0, 0.0, 1.0)
                    else:
                        rotate_matrix = vmath.m33from_axis_rotation(rotate[:3], angle)
                    matrix = vmath.m33mulm44(rotate_matrix, matrix)

            elif child_type == 'scale':
                scale = [ float(x) for x in node_param_e.text.split() ]
                scale_matrix = vmath.m33(scale[0],      0.0,      0.0,
                                              0.0, scale[1],      0.0,
                                              0.0,      0.0, scale[2])
                matrix = vmath.m33mulm44(scale_matrix, matrix)

            elif child_type == 'matrix':
                local_matrix = vmath.m44transpose(tuple([ float(x) for x in node_param_e.text.split() ]))
                matrix = vmath.m44mul(local_matrix, matrix)

        # Hard coded scale
        if global_scale != 1.0:
            matrix = vmath.m44setpos(matrix, vmath.v4muls(vmath.m44pos(matrix), global_scale))

        matrix = vmath.tidy(matrix) # Remove tiny values

        if matrix[ 0] != 1.0 or matrix[ 1] != 0.0 or matrix[ 2] != 0.0 or \
           matrix[ 4] != 0.0 or matrix[ 5] != 1.0 or matrix[ 6] != 0.0 or \
           matrix[ 8] != 0.0 or matrix[ 9] != 0.0 or matrix[10] != 1.0 or \
           matrix[12] != 0.0 or matrix[13] != 0.0 or matrix[14] != 0.0:
            self.matrix = matrix
        else:
            self.matrix = None

        geometries_e = node_e.findall(tag('instance_geometry'))

        for geometry_e in geometries_e:
            geometry_url = tidy_name(geometry_e.get('url'))
            if geometry_url in geometries:
                self.instance_geometry.append(Dae2Node.InstanceGeometry(geometry_e))
            else:
                LOG.warning('INSTANCE_GEOMETRY referencing missing or unprocessed geometry:%s', geometry_url)

        # Remove any references to invalid surfaces in the geometry
        for instance_geometry in self.instance_geometry:
            surfaces_to_remove = []
            geometry = geometries[instance_geometry.geometry]
            for material in instance_geometry.materials:
                if material == 'default':
                    if len(geometry.surfaces) != 1:
                        surfaces_to_remove.append(material)
                        LOG.warning('INSTANCE_GEOMETRY referencing default surface but geometry has surfaces:url:%s',
                                    instance_geometry.geometry)
                elif material not in geometry.surfaces:
                    surfaces_to_remove.append(material)
                    LOG.warning('INSTANCE_GEOMETRY referencing surface not present in geometry:surface:%s:url:%s',
                                material, instance_geometry.geometry)
            for surface in surfaces_to_remove:
                del instance_geometry.materials[surface]

        for light_e in node_e.findall(tag('instance_light')):
            self.lights.append(tidy_name(light_e.get('url')))

        for camera_e in node_e.findall(tag('instance_camera')):
            self.cameras.append(tidy_name(camera_e.get('url')))

        for instance_controller_e in node_e.findall(tag('instance_controller')):
            self.instance_controller.append(Dae2Node.InstanceController(instance_controller_e, global_scale,
                                            controllers_e, None, geometries))

        # Instanced nodes, processed like normal children but with custom prefixes
        for instance_node_e in node_e.findall(tag('instance_node')):
            instance_node_url = instance_node_e.get('url')
            if instance_node_url is not None:
                if instance_node_url[0] == '#':
                    instanced_node_e = find_node(instance_node_url, collada_e)
                    if instanced_node_e is not None:
                        self.children.append(Dae2Node(instanced_node_e, global_scale, self, None, node_name,
                                             controllers_e, collada_e, name_map, node_names, node_map, geometries))
                else:
                    self.references.append(instance_node_url)

        # Children...
        for children_e in node_e.findall(tag('node')):
            self.children.append(Dae2Node(children_e, global_scale, self, None, parent_prefix, controllers_e,
                                          collada_e, name_map, node_names, node_map, geometries))
# pylint: enable=R0913,R0914

    def process(self, nodes):
        for instance_controller in self.instance_controller:
            instance_controller.process(nodes)

        for child in self.children:
            child.process(nodes)

    def attach(self, json_asset, url_handler, name_map):
        node_name = self.path

        json_asset.attach_node(node_name, self.matrix)
        if self.animated:
            node_attrib = { 'dynamic': True }
            json_asset.attach_node_attributes(node_name, node_attrib)

        for light in self.lights:
            json_asset.attach_node_light_instance(node_name, light, find_name(name_map, light))

        # Scene runtime code only supports one camera per node
        if len(self.cameras) == 1:
            json_asset.attach_node_attributes(node_name, {'camera': find_name(name_map, self.cameras[0])} )
        else:
            for camera in self.cameras:
                camera_name = NodeName(node_name.leaf_name() + '-' + camera)
                camera_name.add_parent_node(node_name)
                json_asset.attach_node_attributes(camera_name, {'camera': find_name(name_map, camera)} )

        # !!! We only support references to root nodes
        if len(self.references) == 1 and len(self.instance_geometry) == 0:
            reference_parts = self.references[0].split('#')
            file_name = url_handler.tidy(reference_parts[0])
            json_asset.attach_node_attributes(node_name, { 'reference': file_name, 'inplace': True } )
        else:
            for reference in self.references:
                reference_parts = reference.split('#')
                file_name = url_handler.tidy(reference_parts[0])
                reference_name = NodeName(node_name.leaf_name() + '-' + file_name.replace('/', '-'))
                reference_name.add_parent_node(node_name)
                json_asset.attach_node_attributes(reference_name, { 'reference': file_name,
                                                                    'inplace': True } )
        for instance in self.instance_geometry:
            instance.attach(json_asset, name_map, node_name)
        for instance in self.instance_controller:
            instance.attach(json_asset, name_map, node_name)
        for child in self.children:
            child.attach(json_asset, url_handler, name_map)

class Dae2PhysicsMaterial(object):
    def __init__(self, physics_material_e, name_map):
        self.params = { }

        # Name...
        self.id = physics_material_e.get('id', 'unknown')
        self.name = physics_material_e.get('name', self.id)
        name_map[self.id] = self.name

        # Material...
        technique_e = physics_material_e.find(tag('technique_common'))
        for param_e in technique_e.getchildren():
            param_name = untag(param_e.tag)
            param_text = param_e.text
            self.params[param_name] = float(param_text)

    def attach(self, json_asset):
        json_asset.attach_physics_material(self.name, self.params)

class Dae2PhysicsModel(object):
    def __init__(self, physics_model_e, geometries_nodes_e, rigid_body_map, name_map):
        self.rigidbodys = { }

        # Name...
        self.id = physics_model_e.get('id', 'unknown')
        self.name = physics_model_e.get('name', self.id)
        name_map[self.id] = self.name

        # Rigid Body...
        for rigidbody_e in physics_model_e.findall(tag('rigid_body')):
            technique_e = rigidbody_e.find(tag('technique_common'))
            if technique_e is not None:
                rigidbody = { }
                shape_e = technique_e.find(tag('shape'))
                if shape_e is not None:
                    rigidbody['type'] = 'rigid'

                    instance_geometry_e = shape_e.find(tag('instance_geometry'))
                    if instance_geometry_e is not None:
                        geometry_name = tidy_name(instance_geometry_e.get('url'))
                        rigidbody['geometry'] = find_name(name_map, geometry_name)

                        for geometry_e in geometries_nodes_e.findall(tag('geometry')):
                            geometry_id = geometry_e.get('id')
                            if geometry_id == geometry_name:
                                if geometry_e.find(tag('convex_mesh')) is not None:
                                    rigidbody['shape'] = 'convexhull'
                                else:
                                    rigidbody['shape'] = 'mesh'
                                break
                    else:
                        shape_type_e = shape_e[0]
                        shape_type_name = untag(shape_type_e.tag)
                        if shape_type_name == 'tapered_cylinder':
                            rigidbody['shape'] = 'cone'
                        else:
                            rigidbody['shape'] = shape_type_name

                        radius_e = shape_type_e.find(tag('radius'))
                        if radius_e is None:
                            radius_e = shape_type_e.find(tag('radius1'))
                        if radius_e is not None:
                            radius_list = [float(x) for x in radius_e.text.split()]
                            rigidbody['radius'] = radius_list[0] # !!! What about the other values

                        height_e = shape_type_e.find(tag('height'))
                        if height_e is not None:
                            rigidbody['height'] = float(height_e.text)

                        half_extents_e = shape_type_e.find(tag('half_extents'))
                        if half_extents_e is not None:
                            rigidbody['halfExtents'] = [float(x) for x in half_extents_e.text.split()]

                    material_e = shape_e.find(tag('instance_physics_material'))
                    if material_e is not None:
                        material_name = tidy_name(material_e.get('url'))
                        rigidbody['material'] = find_name(name_map, material_name)

                material_e = technique_e.find(tag('instance_physics_material'))
                if material_e is not None:
                    material_name = tidy_name(material_e.get('url'))
                    rigidbody['material'] = find_name(name_map, material_name)

                dynamic_e = technique_e.find(tag('dynamic'))
                if dynamic_e is not None:
                    value = dynamic_e.text.lower()
                    if value == 'true':
                        rigidbody['dynamic'] = True

                        mass_e = technique_e.find(tag('mass'))
                        if mass_e is not None:
                            rigidbody['mass'] = float(mass_e.text)

                        inertia_e = technique_e.find(tag('inertia'))
                        if inertia_e is not None:
                            inertia = [float(x) for x in inertia_e.text.split()]
                            if inertia[0] != 0.0 or inertia[1] != 0.0 or inertia[2] != 0.0:
                                rigidbody['inertia'] = inertia

                if len(rigidbody) > 0:
                    rigidbody_id = rigidbody_e.get('id', 'unknown')
                    rigidbody_name = rigidbody_e.get('name', rigidbody_id)
                    name_map[rigidbody_id] = rigidbody_name
                    rigid_body_map[rigidbody_id] = rigidbody
                    self.rigidbodys[rigidbody_name] = rigidbody

    def attach(self, json_asset):
        for name, rigidbody in self.rigidbodys.iteritems():
            json_asset.attach_physics_model(name, model=rigidbody)

class Dae2InstancePhysicsModel(object):

    class InstanceRigidBody(object):
        def __init__(self, name, body_name, target, params, parent_url):
            self.name = name
            self.body_name = body_name
            self.target = target
            self.params = params
            self.parent_url = parent_url

        def attach(self, json_asset, rigid_body_map, name_map, node_map):
            body_name = find_scoped_name(self.body_name, self.parent_url, name_map)
            body = find_scoped_node(self.body_name, self.parent_url, rigid_body_map)
            if not body:
                LOG.warning('Rigid body instance references an unknown physics model: %s -> %s',
                            self.name, self.body_name)
            target = node_map.get(self.target, None)
            if target:
                target_name = target.path
                # Check for non-root dynamic objects
                target_path = str(target_name)
                if '/' in target_path:
                    if body and body.get('dynamic', False):
                        LOG.error('Dynamic rigid body targets non-root graphics node: %s -> %s',
                                  body_name, target_path)
            else:
                target_name = NodeName(find_name(name_map, self.target))

            params = self.params
            if len(params) > 0:
                if body and 'dynamic' in params and params['dynamic'] != body.get('dynamic', False):
                    body_name = body_name + ':' + self.name
                    LOG.warning('Cloning ridig body because instance has conflicting dynamic properties: ' + body_name)
                    body = dict(body)
                    body['dynamic'] = params['dynamic']
                    del params['dynamic']
                    if 'mass' in params:
                        body['mass'] = params['mass']
                        del params['mass']
                    if 'inertia' in params:
                        body['inertia'] = params['inertia']
                        del params['inertia']
                json_asset.attach_physics_model(body_name, model=body)

                json_asset.attach_physics_node(self.name, body_name, target_name, params)
            else:
                json_asset.attach_physics_node(self.name, body_name, target_name)

    def __init__(self, physics_node_e):
        self.instance_rigidbodys = [ ]

        # Name...
        self.name = tidy_name(physics_node_e.get('url'))

        # Nodes...
        for node_index, rigid_body_e in enumerate(physics_node_e.findall(tag('instance_rigid_body'))):
            if node_index > 0:
                node_name = "%s-%u" % (self.name, node_index)
            else:
                node_name = self.name

            body_name = rigid_body_e.get('body')
            target = tidy_name(rigid_body_e.get('target'))
            params = { }

            technique_e = rigid_body_e.find(tag('technique_common'))
            if technique_e is not None:
                angular_velocity_e = technique_e.find(tag('angular_velocity'))
                if angular_velocity_e is not None:
                    velocity = [float(x) for x in angular_velocity_e.text.split()]
                    if velocity[0] != 0.0 or velocity[1] != 0.0 or velocity[2] != 0.0:
                        params['angularvelocity'] = velocity

                velocity_e = technique_e.find(tag('velocity'))
                if velocity_e is not None:
                    velocity = [float(x) for x in velocity_e.text.split()]
                    if velocity[0] != 0.0 or velocity[1] != 0.0 or velocity[2] != 0.0:
                        params['velocity'] = velocity

                dynamic_e = technique_e.find(tag('dynamic'))
                if dynamic_e is not None:
                    value = dynamic_e.text.lower()
                    if value == 'true':
                        params['dynamic'] = True

                        mass_e = technique_e.find(tag('mass'))
                        if mass_e is not None:
                            params['mass'] = float(mass_e.text)

                        inertia_e = technique_e.find(tag('inertia'))
                        if inertia_e is not None:
                            inertia = [float(x) for x in inertia_e.text.split()]
                            if inertia[0] != 0.0 or inertia[1] != 0.0 or inertia[2] != 0.0:
                                params['inertia'] = inertia

            rigidbody = Dae2InstancePhysicsModel.InstanceRigidBody(node_name, body_name, target, params, self.name)
            self.instance_rigidbodys.append(rigidbody)

    def attach(self, json_asset, physics_models, name_map, node_map):
        for rigidbody in self.instance_rigidbodys:
            rigidbody.attach(json_asset, physics_models, name_map, node_map)

#######################################################################################################################

class Dae2Animation(object):
    def __init__(self, animation_e, library_animations_e, name_map, animations_list):
        self.name = None
        self.sources = { }
        self.samplers = { }
        self.channels = [ ]
        self.children = [ ]

        # Name...
        self.id = animation_e.get('id', 'unknown')
        self.name = animation_e.get('name', self.id)
        LOG.debug('ANIMATION:%s', self.name)
        name_map[self.id] = self.name

        # Animation children
        animation_children_e = animation_e.findall(tag('animation'))
        for a in animation_children_e:
            child = Dae2Animation(a, library_animations_e, name_map, animations_list)
            if child.id != 'unknown':
                animations_list[child.id] = child
            self.children.append(child)

        # Sources...
        source_e = animation_e.findall(tag('source'))
        for s in source_e:
            technique_e = s.find(tag('technique_common'))
            accessor_e = technique_e.find(tag('accessor'))
            param_e = accessor_e.find(tag('param'))
            param_name = param_e.get('name')
            if param_e.get('type').lower() == 'name':
                array_e = s.find(tag('Name_array'))
                count = int(array_e.get('count', '0'))
                if (0 < count):
                    values_text = array_e.text
                    self.sources[s.get('id')] = { 'name': param_name, 'values': values_text.split() }
            else:
                array_e = s.find(tag('float_array'))
                count = int(array_e.get('count', '0'))
                stride = int(accessor_e.get('stride', '1'))
                if (0 < count):
                    values_text = array_e.text
                    float_values = [float(x) for x in values_text.split()]
                    if stride == 1:
                        values = float_values
                    else:
                        values = []
                        for i in range(0, count, stride):
                            values.append(float_values[i:i+stride])
                    self.sources[s.get('id')] = { 'name': param_name, 'values': values }

        sampler_e = animation_e.findall(tag('sampler'))
        for s in sampler_e:
            sampler_id = s.get('id')
            inputs = { }
            inputs_e = s.findall(tag('input'))
            for i in inputs_e:
                inputs[i.get('semantic')] = tidy_name(i.get('source'))
            self.samplers[sampler_id] = { 'inputs': inputs }

        channel_e = animation_e.findall(tag('channel'))
        for c in channel_e:
            sampler = tidy_name(c.get('source'))
            target = c.get('target')
            self.channels.append({ 'sampler': sampler, 'target': target})

        #print self.sources
        #print self.samplers
        #print self.channels

    def evaluate(self, time, sampler_id):
        sampler = self.samplers[sampler_id]
        times = self.sources[sampler['inputs']['INPUT']]['values']
        values = self.sources[sampler['inputs']['OUTPUT']]['values']
        interpolation = self.sources[sampler['inputs']['INTERPOLATION']]['values']

        if len(times) == 0 or len(values) == 0:
            LOG.error('Animation evaluation failed due to missing times or values in:%s', self.name)
        if len(times) != len(values):
            LOG.error('Animation evaluation failed due to mismatch in count of times and values in:%s', self.name)

        if time < times[0]:
            return values[0]
        if time > times[len(times)-1]:
            return values[len(values)-1]
        for i, t in enumerate(times):
            if t == time:
                return values[i]
            elif t > time:
                start_key = i - 1
                end_key = i
                if interpolation[start_key] != 'LINEAR':
                    LOG.warning('Animation evaluation linear sampling non linear keys of type:%s:in animation:%s',
                                interpolation[start_key], self.name)
                start_time = times[start_key]
                end_time = t
                delta = (time - start_time) / (end_time - start_time)
                start_val = values[start_key]
                end_val = values[end_key]
                if type(start_val) is float:
                    return (start_val + delta * (end_val - start_val))
                else:
                    if len(start_val) != len(end_val):
                        LOG.error('Animation evaluation failed in animation:%s:due to mismatched keyframe sizes',
                                  self.name)
                    result = []
                    for v in xrange(0, len(start_val)):
                        val1 = start_val[v]
                        val2 = end_val[v]
                        result.append(val1 + delta * (val2 - val1))
                    return result

        LOG.warning('Animation evaluation failed in animation:%s', self.name)
        return values[0]



#######################################################################################################################

def _decompose_matrix(matrix, node):
    sx = vmath.v3length(vmath.m43right(matrix))
    sy = vmath.v3length(vmath.m43up(matrix))
    sz = vmath.v3length(vmath.m43at(matrix))
    det = vmath.m43determinant(matrix)
    if not vmath.v3equal(vmath.v3create(sx, sy, sz), vmath.v3create(1, 1, 1)) or det < 0:
        if det < 0:
            LOG.warning('Detected negative scale in node "%s", not currently supported', node.name)
            sx *= -1
        if sx != 0:
            matrix = vmath.m43setright(matrix, vmath.v3muls(vmath.m43right(matrix), 1 / sx))
        else:
            matrix = vmath.m43setright(matrix, vmath.V3XAXIS)
        if sy != 0:
            matrix = vmath.m43setup(matrix, vmath.v3muls(vmath.m43up(matrix), 1 / sy))
        else:
            matrix = vmath.m43setup(matrix, vmath.V3YAXIS)
        if sz != 0:
            matrix = vmath.m43setat(matrix, vmath.v3muls(vmath.m43at(matrix), 1 / sz))
        else:
            matrix = vmath.m43setat(matrix, vmath.V3ZAXIS)
    else:
        sx = 1
        sy = 1
        sz = 1
    quat = vmath.quatfrom_m43(matrix)
    pos = vmath.m43pos(matrix)
    scale = vmath.v3create(sx, sy, sz)
    return (quat, pos, scale)

def _evaluate_node(node, time, target_data, global_scale):
    identity_matrix = vmath.M44IDENTITY
    matrix = identity_matrix

    node_e = node.element
    node_id = node_e.get('id')
    for node_param_e in node_e:
        overloads = []
        if target_data:
            if 'sid' in node_param_e.attrib:
                sid = node_param_e.attrib['sid']

                for anim in target_data['anims']:
                    for channel in anim.channels:
                        (target_node_id, _, parameter) = channel['target'].partition('/')
                        (target_sid, _, target_attrib) = parameter.partition('.')
                        if target_node_id == node_id and target_sid == sid:
                            overloads.append((target_attrib, anim.evaluate(time, channel['sampler'])))

        child_type = untag(node_param_e.tag)
        if child_type == 'translate':
            offset = [ float(x) for x in node_param_e.text.split() ]
            for overload_attrib, overload_value in overloads:
                if overload_attrib == 'X':
                    offset[0] = overload_value
                elif overload_attrib == 'Y':
                    offset[1] = overload_value
                elif overload_attrib == 'Z':
                    offset[2] = overload_value
                elif overload_attrib == '':
                    offset = overload_value

            translate_matrix = vmath.m43(1.0, 0.0, 0.0,
                                         0.0, 1.0, 0.0,
                                         0.0, 0.0, 1.0,
                                         offset[0], offset[1], offset[2])
            matrix = vmath.m43mulm44(translate_matrix, matrix)

        elif child_type == 'rotate':
            rotate = [ float(x) for x in node_param_e.text.split() ]
            for overload_attrib, overload_value in overloads:
                if isinstance(overload_value, list):
                    rotate[0] = overload_value[0]
                    rotate[1] = overload_value[1]
                    rotate[2] = overload_value[2]
                    rotate[3] = overload_value[3]
                else:
                    rotate[3] = overload_value
            if rotate[3] != 0.0:
                angle = rotate[3] / 180.0 * math.pi
                if rotate[0] == 1.0 and rotate[1] == 0.0 and rotate[2] == 0.0:
                    c = math.cos(angle)
                    s = math.sin(angle)
                    rotate_matrix = vmath.m33(1.0, 0.0, 0.0,
                                              0.0,   c,   s,
                                              0.0,  -s,   c)
                elif rotate[0] == 0.0 and rotate[1] == 1.0 and rotate[2] == 0.0:
                    c = math.cos(angle)
                    s = math.sin(angle)
                    rotate_matrix = vmath.m33(  c, 0.0,  -s,
                                              0.0, 1.0, 0.0,
                                                s, 0.0,   c)
                elif rotate[0] == 0.0 and rotate[1] == 0.0 and rotate[2] == 1.0:
                    c = math.cos(angle)
                    s = math.sin(angle)
                    rotate_matrix = vmath.m33(  c,   s, 0.0,
                                               -s,   c, 0.0,
                                              0.0, 0.0, 1.0)
                else:
                    rotate_matrix = vmath.m33from_axis_rotation(rotate[:3], angle)
                matrix = vmath.m33mulm44(rotate_matrix, matrix)

        elif child_type == 'scale':
            scale = [ float(x) for x in node_param_e.text.split() ]
            for overload_attrib, overload_value in overloads:
                if overload_attrib == 'X':
                    scale[0] = overload_value
                elif overload_attrib == 'Y':
                    scale[1] = overload_value
                elif overload_attrib == 'Z':
                    scale[2] = overload_value
                elif overload_attrib == '':
                    scale = overload_value
            scale_matrix = vmath.m33(scale[0],      0.0,      0.0,
                                          0.0, scale[1],      0.0,
                                          0.0,      0.0, scale[2])
            matrix = vmath.m33mulm44(scale_matrix, matrix)

        elif child_type == 'matrix':
            if len(overloads) > 1:
                LOG.warning('Found multiple matrices animating a single node')
            if overloads:
                for overload_attrib, overload_value in overloads:
                    local_matrix = vmath.m44transpose(overload_value)
            else:
                local_matrix = vmath.m44transpose([ float(x) for x in node_param_e.text.split() ])
            if matrix != identity_matrix:
                matrix = vmath.m44mul(local_matrix, matrix)
            else:
                matrix = local_matrix

    # Hard coded scale
    if global_scale != 1.0:
        matrix = vmath.m44setpos(matrix, vmath.v4muls(vmath.m44pos(matrix), global_scale))

    matrix = vmath.tidy(matrix) # Remove tiny values

    return vmath.m43from_m44(matrix)

class Dae2AnimationClip(object):
    # pylint: disable=R0914
    def __init__(self, animation_clip_e, global_scale, upaxis_rotate, library_animation_clips_e, name_map, animations,
                 nodes, default_root):
        self.name = None
        self.scale = global_scale
        self.source_anims = [ ]
        self.anim = None

        # Name...
        if not default_root:
            self.id = animation_clip_e.get('id', 'unknown')
            self.name = animation_clip_e.get('name', self.id)
        else:
            name = 'default_' + default_root
            self.id = name
            self.name = name
        LOG.debug('ANIMATION:%s', self.name)
        name_map[self.id] = self.name

        def add_anim_and_children(anim, anim_list):
            anim_list.append(anim)
            for child in anim.children:
                add_anim_and_children(child, anim_list)

        if not default_root:
            for instance_animation_e in animation_clip_e.findall(tag('instance_animation')):
                anim = animations[tidy_name(instance_animation_e.get('url'))]
                if anim is not None:
                    add_anim_and_children(anim, self.source_anims)
        else:
            for anim in animations:
                add_anim_and_children(animations[anim], self.source_anims)

        # TODO: move the following code to process method

        #   { 'num_frames': 2,
        #     'numNodes' : 3,
        #     'frame_rate': 30,
        #     'hiearchy': { 'joints': ['root', -1, [0,0,0,1], [0,0,0]] },
        #     'bounds': [ { 'center': [0,0,0], 'halfExtent': [10,10,10] } ],
        #     'joint_data': [ { 'time': 0, 'rotation': [0,0,0,1], 'translation': [0,0,0] } ]

        global_times = []

        def __find_node_in_dict(node_dict, node_name):

            def __find_node(node_root, node_name):
                if node_root.id == node_name:
                    return node_root

                if node_root.children:
                    for c in node_root.children:
                        result = __find_node(c, node_name)
                        if result:
                            return result
                return None

            for n in node_dict:
                result = __find_node(node_dict[n], node_name)
                if result:
                    return result
            return None

        def __node_root(node_name, nodes):
            node = __find_node_in_dict(nodes, node_name)
            if node is None:
                return None
            while node.parent:
                node = node.parent

            return node.id

        def __is_node(node_name, nodes):
            node = __find_node_in_dict(nodes, node_name)
            return node is not None

        # Work out the list of keyframe times and animations required for each target
        targets = {}
        for anim in self.source_anims:
            for channel in anim.channels:
                target_parts = channel['target'].split('/')
                target = target_parts[0]
                target_channel = target_parts[1]

                if __is_node(target, nodes) and target_channel != 'visibility':
                    # for default animations reject targets which aren't under the same hierarchy
                    if not default_root or default_root == __node_root(target, nodes):
                        sampler = anim.samplers[channel['sampler']]
                        sampler_input = sampler['inputs']['INPUT']
                        if sampler_input in anim.sources:
                            if not target in targets:
                                targets[target] = { 'anims': [], 'keyframe_times': [] }
                            if anim not in targets[target]['anims']:
                                targets[target]['anims'].append(anim)

                            # Find all the keyframe times for the animation
                            times = targets[target]['keyframe_times']
                            time_inputs = anim.sources[sampler_input]
                            if time_inputs['name'] == 'TIME':
                                for t in time_inputs['values']:
                                    if t not in times:
                                        times.append(t)
                                    if t not in global_times:
                                        global_times.append(t)

        if len(targets) == 0:
            return

        # Build a hierarchy from the keys in targets and any intermediate nodes (or nodes in the skin)
        start_joints = targets.keys()
        hierarchy = build_joint_hierarchy(start_joints, nodes)
        runtime_joint_names = [ ]
        runtime_joint_parents = [ ]
        for joint in hierarchy:
            runtime_joint_names.append(joint['node'].name)
            runtime_joint_parents.append(joint['parent'])

        joint_hierarchy = {
            'numNodes': len(runtime_joint_names),
            'names': runtime_joint_names,
            'parents': runtime_joint_parents
            }

        # Work out the start and end time for the animation
        global_times = sorted(global_times)
        start_time = global_times[0]
        end_time = global_times[len(global_times)-1]

        # TODO: reenable when sampling between keys works
        #if not default_root:
        #    start_time = animation_clip_e.get('start', start_time)
        #    end_time = animation_clip_e.get('end', end_time)

        # Work out animation lengths and keyframe counts
        anim_length = end_time - start_time

        # Generate some joint data for the animation
        frames = [ ]

        for j, joint in enumerate(hierarchy):
            orig_index = joint['orig_index']
            if orig_index is not -1:
                target_name = start_joints[orig_index]
            else:
                target_name = None
            node = joint['node']
            node.animated = True
            joint_data = [ ]
            if target_name is not None and target_name in targets:
                target_data = targets[target_name]
                key_times = target_data['keyframe_times']
                key_times = sorted(key_times)
                if key_times[0] > start_time:
                    key_times.insert(0, start_time)
                if key_times[len(key_times) - 1] < end_time:
                    key_times.append(end_time)
                for t in key_times:
                    node_matrix = _evaluate_node(node, t, target_data, global_scale)
                    qps = _decompose_matrix(node_matrix, node)
                    frame_time = t - start_time
                    joint_data.append({'time': frame_time, 'rotation': qps[0], 'translation': qps[1], 'scale': qps[2] })
            else:
                # no targets so we simply add a start key
                node_matrix = _evaluate_node(node, start_time, None, global_scale)
                qps = _decompose_matrix(node_matrix, node)
                joint_data.append({'time': 0, 'rotation': qps[0], 'translation': qps[1], 'scale': qps[2] })

            # TODO: remove translation of [0, 0, 0]
            channels = { 'rotation': True, 'translation': True }
            base_frame = { }
            if len(joint_data) > 1:
                varying_rotation = False
                varying_translation = False
                varying_scale = False
                init_rotation = joint_data[0]['rotation']
                init_translation = joint_data[0]['translation']
                init_scale = joint_data[0]['scale']
                for f in joint_data[1:]:
                    if varying_rotation or f['rotation'] != init_rotation:
                        varying_rotation = True
                    if varying_translation or f['translation'] != init_translation:
                        varying_translation = True
                    if varying_scale or f['scale'] != init_scale:
                        varying_scale = True
                if not varying_rotation:
                    base_frame['rotation'] = init_rotation
                    for f in joint_data:
                        del f['rotation']
                if not varying_translation:
                    base_frame['translation'] = init_translation
                    for f in joint_data:
                        del f['translation']
                if not varying_scale:
                    if not vmath.v3equal(init_scale, vmath.v3create(1, 1, 1)):
                        base_frame['scale'] = init_scale
                        channels['scale'] = True
                    for f in joint_data:
                        del f['scale']
                else:
                    channels['scale'] = True
            elif len(joint_data) == 1:
                init_rotation = joint_data[0]['rotation']
                init_translation = joint_data[0]['translation']
                init_scale = joint_data[0]['scale']
                base_frame = { 'rotation': init_rotation,
                               'translation': init_translation }
                if not vmath.v3equal(init_scale, vmath.v3create(1, 1, 1)):
                    base_frame['scale'] = init_scale
                    channels['scale'] = True
                joint_data = None

            frame_data = { 'channels': channels }
            if joint_data is not None:
                frame_data['keyframes'] = joint_data
            if len(base_frame.keys()):
                frame_data['baseframe'] = base_frame
            frames.append( frame_data )

        # Work out what channels of data are included in the animation
        channel_union = set(frames[0]['channels'].keys())
        uniform_channels = True
        for f in frames[1:]:
            if not uniform_channels or channel_union.symmetric_difference(f['channels'].keys()):
                channel_union = channel_union.union(f['channels'].keys())
                uniform_channels = False

        if uniform_channels:
            # if we have the same channels on all nodes then don't replicate the info
            for f in frames:
                del f['channels']

        # Generate some bounds, for now we calculate the bounds of the root nodes animation and extend them
        # by the length of the joint hierarchy
        maxflt = sys.float_info.max
        bound_min = vmath.v3create(maxflt, maxflt, maxflt)
        bound_max = vmath.v3create(-maxflt, -maxflt, -maxflt)

        joint_lengths = [0] * len(hierarchy)
        for j, joint in enumerate(hierarchy):
            parent_index = joint['parent']
            if parent_index is -1:
                if 'baseframe' in frames[j] and 'translation' in frames[j]['baseframe']:
                    bound_min = vmath.v3min(bound_min, frames[j]['baseframe']['translation'])
                    bound_max = vmath.v3max(bound_max, frames[j]['baseframe']['translation'])
                else:
                    f = frames[j]['keyframes']
                    for frame in f:
                        bound_min = vmath.v3min(bound_min, frame['translation'])
                        bound_max = vmath.v3max(bound_max, frame['translation'])
                joint_lengths[j] = 0
            else:
                if 'baseframe' in frames[j] and 'translation' in frames[j]['baseframe']:
                    bone_length = vmath.v3length(frames[j]['baseframe']['translation'])
                else:
                    bone_length = vmath.v3length(frames[j]['keyframes'][0]['translation'])
                joint_lengths[j] = joint_lengths[parent_index] + bone_length

        max_joint_length = max(joint_lengths)

        bounds = []
        center = vmath.v3muls(vmath.v3add(bound_min, bound_max), 0.5)
        half_extent = vmath.v3sub(center, bound_min)
        half_extent = vmath.v3add(half_extent, vmath.v3create(max_joint_length, max_joint_length, max_joint_length))
        bounds.append({'time': 0, 'center': center, 'halfExtent': half_extent })
        bounds.append({'time': anim_length, 'center': center, 'halfExtent': half_extent })

        self.anim = { 'length': anim_length,
                      'numNodes': len(joint_hierarchy['names']),
                      'hierarchy': joint_hierarchy,
                      'channels': dict.fromkeys(channel_union, True),
                      'nodeData': frames,
                      'bounds': bounds }
    # pylint: enable=R0914

    def attach(self, json_asset, name_map):
        json_asset.attach_animation(self.name, self.anim)

#######################################################################################################################

# pylint: disable=R0914
def parse(input_filename="default.dae", output_filename="default.json", asset_url="", asset_root=".", infiles=None,
          options=None):
    """Untility function to convert a Collada file into a JSON file."""

    definitions_asset = standard_include(infiles)

    animations = { }
    animation_clips = { }
    geometries = { }
    effects = { }
    materials = { }
    images = { }
    lights = { }
    nodes = { }
    physics_materials = { }
    physics_models = { }
    physics_bodies = { }
    physics_nodes = { }

    name_map = { }
    geometry_names = { }
    effect_names = { }
    light_names = { }
    node_names = { }
    node_map = { }

    url_handler = UrlHandler(asset_root, input_filename)

    # DOM stuff from here...
    try:
        collada_e = ElementTree.parse(input_filename).getroot()
    except IOError as e:
        LOG.error('Failed loading: %s', input_filename)
        LOG.error('  >> %s', e)
        exit(1)
    except ExpatError as e:
        LOG.error('Failed processing: %s', input_filename)
        LOG.error('  >> %s', e)
        exit(2)
    else:
        if collada_e is not None:
            fix_sid(collada_e, None)

            # Asset...
            asset_e = collada_e.find(tag('asset'))

            # What is the world scale?
            scale = 1.0
            unit_e = asset_e.find(tag('unit'))
            if unit_e is not None:
                scale = float(unit_e.get('meter', '1.0'))

            # What is the up axis?
            upaxis_rotate = None
            upaxis_e = asset_e.find(tag('up_axis'))
            if upaxis_e is not None:
                if upaxis_e.text == 'X_UP':
                    upaxis_rotate = [ 0.0, 1.0, 0.0, 0.0,
                                     -1.0, 0.0, 0.0, 0.0,
                                      0.0, 0.0, 1.0, 0.0,
                                      0.0, 0.0, 0.0, 1.0 ]
                elif upaxis_e.text == 'Z_UP':
                    upaxis_rotate = [ 1.0, 0.0,  0.0, 0.0,
                                      0.0, 0.0, -1.0, 0.0,
                                      0.0, 1.0,  0.0, 0.0,
                                      0.0, 0.0,  0.0, 1.0 ]
                LOG.info('Up axis:%s', upaxis_e.text)

            # Core COLLADA elements are:
            #
            # library_animation_clips       - not supported
            # library_animations            - not supported
            # instance_animation            - not supported
            # library_cameras               - not supported
            # instance_camera               - supported
            # library_controllers           - not supported
            # instance_controller           - supported
            # library_geometries            - supported
            # instance_geometry             - supported
            # library_lights                - supported
            # instance_light                - supported
            # library_nodes                 - not supported
            # instance_node                 - supported
            # library_visual_scenes         - supported
            # instance_visual_scene         - not supported
            # scene                         - not supported

            geometries_e = collada_e.find(tag('library_geometries'))
            if geometries_e is not None:
                for x in geometries_e.findall(tag('geometry')):
                    g = Dae2Geometry(x, scale, geometries_e, name_map, geometry_names)
                    # For now we only support mesh and convex_mesh
                    if g.type == 'mesh' or g.type == 'convex_mesh':
                        geometries[g.id] = g
            else:
                LOG.warning('Collada file without:library_geometries:%s', input_filename)

            lights_e = collada_e.find(tag('library_lights'))
            if lights_e is not None:
                for x in lights_e.findall(tag('light')):
                    l = Dae2Light(x, name_map, light_names)
                    lights[l.id] = l

            controllers_e = collada_e.find(tag('library_controllers'))
            visual_scenes_e = collada_e.find(tag('library_visual_scenes'))
            if visual_scenes_e is not None:
                visual_scene_e = visual_scenes_e.findall(tag('visual_scene'))
                if visual_scene_e is not None:
                    if len(visual_scene_e) > 1:
                        LOG.warning('Collada file with more than 1:visual_scene:%s', input_filename)
                    node_e = visual_scene_e[0].findall(tag('node'))
                    for n in node_e:
                        n = Dae2Node(n, scale, None, upaxis_rotate, None, controllers_e, collada_e,
                                     name_map, node_names, node_map, geometries)
                        nodes[n.id] = n
                    if len(node_e) == 0:
                        LOG.warning('Collada file without:node:%s', input_filename)
                else:
                    LOG.warning('Collada file without:visual_scene:%s', input_filename)
            else:
                LOG.warning('Collada file without:library_visual_scenes:%s', input_filename)

            animations_e = collada_e.find(tag('library_animations'))
            if animations_e is not None:
                for x in animations_e.findall(tag('animation')):
                    a = Dae2Animation(x, animations_e, name_map, animations)
                    animations[a.id] = a

            animation_clips_e = collada_e.find(tag('library_animation_clips'))
            if animation_clips_e is not None:
                for x in animation_clips_e.findall(tag('animation_clip')):
                    c = Dae2AnimationClip(x, scale, upaxis_rotate, animation_clips_e, name_map, animations, nodes, None)
                    animation_clips[c.id] = c
            else:
                if animations_e is not None:
                    LOG.info('Exporting default animations from:%s', input_filename)
                    for n in nodes:
                        c = Dae2AnimationClip(x, scale, upaxis_rotate, None, name_map, animations, nodes, n)
                        if c.anim:
                            animation_clips[c.id] = c


            # FX COLLADA elements are:
            #
            # library_effects               - supported
            # instance_effect               - supported
            # library_materials             - supported
            # instance_material             - supported
            # library_images                - supported
            # instance_image                - not supported

            # Images have to be read before effects and materials
            images_e = collada_e.find(tag('library_images'))
            if images_e is not None:
                for x in images_e.findall(tag('image')):
                    i = Dae2Image(x, url_handler, name_map)
                    images[i.id] = i

            effects_e = collada_e.find(tag('library_effects'))
            if effects_e is not None:
                for x in effects_e.iter(tag('image')):
                    i = Dae2Image(x, url_handler, name_map)
                    images[i.id] = i

                for x in effects_e.findall(tag('effect')):
                    e = Dae2Effect(x, url_handler, name_map, effect_names)
                    effects[e.id] = e
            else:
                LOG.warning('Collada file without:library_effects:%s', input_filename)
                # json.AddObject("default")
                # json.AddString("type", "lambert")

            materials_e = collada_e.find(tag('library_materials'))
            if materials_e is not None:
                for x in materials_e.findall(tag('material')):
                    m = Dae2Material(x, name_map)
                    materials[m.id] = m
            else:
                LOG.warning('Collada file without:library_materials:%s', input_filename)
                # json.AddObject("default")
                # json.AddString("effect", "default")

            # Physics COLLADA elements are:
            #
            # library_force_fields          - not supported
            # instance_force_field          - not supported
            # library_physics_materials     - supported
            # instance_physics_material     - supported
            # library_physics_models        - supported
            # instance_physics_model        - supported
            # library_physics_scenes        - supported
            # instance_physics_scene        - not supported
            # instance_rigid_body           - supported
            # instance_rigid_constraint     - not supported

            physics_materials_e = collada_e.find(tag('library_physics_materials'))
            if physics_materials_e is not None:
                for x in physics_materials_e.findall(tag('physics_material')):
                    m = Dae2PhysicsMaterial(x, name_map)
                    physics_materials[m.id] = m

            physics_models_e = collada_e.find(tag('library_physics_models'))
            if physics_models_e is not None:
                for x in physics_models_e.findall(tag('physics_model')):
                    m = Dae2PhysicsModel(x, geometries_e, physics_bodies, name_map)
                    physics_models[m.id] = m

            physics_scenes_e = collada_e.find(tag('library_physics_scenes'))
            if physics_scenes_e is not None:
                physics_scene_e = physics_scenes_e.findall(tag('physics_scene'))
                if physics_scene_e is not None:
                    if len(physics_scene_e) > 1:
                        LOG.warning('Collada file with more than 1:physics_scene:%s', input_filename)
                    for x in physics_scene_e[0].findall(tag('instance_physics_model')):
                        i = Dae2InstancePhysicsModel(x)
                        physics_nodes[i.name] = i

            # Drop reference to the etree
            collada_e = None

    # Process asset...
    for _, node in nodes.iteritems():
        node.process(nodes)

    for _, geometry in geometries.iteritems():
        geometry.process(definitions_asset, nodes, options.nvtristrip, materials, effects)

    # Create JSON...
    json_asset = JsonAsset()

    def _attach(asset_type):
        if options.include_types is not None:
            return asset_type in options.include_types
        if options.exclude_types is not None:
            return asset_type not in options.exclude_types
        return True

    # By default attach images map
    if _attach('images'):
        for _, image in images.iteritems():
            image.attach(json_asset)

    if _attach('effects'):
        for _, effect in effects.iteritems():
            effect.attach(json_asset, definitions_asset)

    if _attach('materials'):
        for _, material in materials.iteritems():
            material.attach(json_asset, definitions_asset, name_map)

    if _attach('geometries'):
        for _, geometry in geometries.iteritems():
            geometry.attach(json_asset)

    if _attach('lights'):
        for _, light in lights.iteritems():
            light.attach(json_asset, definitions_asset)

    if _attach('nodes'):
        for _, node in nodes.iteritems():
            node.attach(json_asset, url_handler, name_map)

    if _attach('animations'):
        for _, animation_clip in animation_clips.iteritems():
            animation_clip.attach(json_asset, name_map)

    if _attach('physicsmaterials'):
        for _, physics_material in physics_materials.iteritems():
            physics_material.attach(json_asset)

    if _attach('physicsnodes'):
        for _, physics_node in physics_nodes.iteritems():
            physics_node.attach(json_asset, physics_bodies, name_map, node_map)

    if _attach('physicsmodels'):
        for _, physics_model in physics_models.iteritems():
            physics_model.attach(json_asset)

    if not options.keep_unused_images:
        remove_unreferenced_images(json_asset)

    # Write JSON...
    try:
        standard_json_out(json_asset, output_filename, options)
    except IOError as e:
        LOG.error('Failed processing: %s', output_filename)
        LOG.error('  >> %s', e)
        exit(3)

    return json_asset
# pylint: enable=R0914

def main():
    description = "Convert Collada (.dae) files into a Turbulenz JSON asset."

    parser = standard_parser(description)
    parser.add_option("--nvtristrip", action="store", dest="nvtristrip", default=None,
            help="path to NvTriStripper, setting this enables "
            "vertex cache optimizations")

    standard_main(parse, __version__, description, __dependencies__, parser)

if __name__ == "__main__":
    exit(main())
