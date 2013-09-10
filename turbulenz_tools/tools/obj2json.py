#!/usr/bin/python
# Copyright (c) 2009-2013 Turbulenz Limited
"""
Convert LightWave (.obj) OBJ2 files into a Turbulenz JSON asset.

Supports generating NBTs.
"""

import logging
LOG = logging.getLogger('asset')

# pylint: disable=W0403
from stdtool import standard_main, standard_json_out, standard_include
from asset2json import JsonAsset
from mesh import Mesh
from node import NodeName
from os.path import basename
# pylint: enable=W0403

__version__ = '1.2.2'
__dependencies__ = ['asset2json', 'mesh', 'node', 'vmath']


DEFAULT_EFFECT_NAME = 'lambert'

# Note:
# * Does not have support for .mtl files yet, but expects any relevant materials
#   to be declared in a .material file and included as a dependancy in deps.yaml
# * This script sets the default node name of the asset parsed to be the file name (without the path),
#   unless anything else is supplied. This could lead to clashes with other nodes with the same name.
# * Each surface is assumed to only have a single material. A new surface will be made upon requiring a new material.

#######################################################################################################################

def _increment_name(name):
    """Returns a name similar to the inputted name

        If the inputted name ends with a hyphen and then a number,
        then the outputted name has that number incremented.
        Otherwise, the outputted name has a hyphen and the number '1' appended to it.
    """
    index = name.rfind('-')
    if index == -1:
        # The is not already followed by a number, so just append -1
        return name + '-1'
    else:
        # The number is already followed by a number, so increment the number
        value = int(name[index+1:])
        return name[:index+1] + str(value+1)

def purge_empty(dictionary, recurseOnce = False):
    """Removes all elements of a dictionary which return true for elem.is_empty().

        If recurseOnce is True, then it will call element.purge_empty()
        for any remaining elements in the dictionary. This will not recurse further."""
    names_empty = []
    for name, elem in dictionary.iteritems():
        if elem.is_empty():
            names_empty.append(name)
    # Need to compile the list of names of empty elements in a separate loop above,
    # to avoid changing dictionary during iteration over it directly.
    for name in names_empty:
        del dictionary[name]
    if recurseOnce:
        for elem in dictionary.itervalues():
            # Note that it is here assumed that the element has a method purge_empty
            elem.purge_empty()


#######################################################################################################################

class Surface(object):
    """Represents a surface (a.k.a. group) as parsed from the .obj file into .json format

        Contains a material, and indices into the Obj2json.primitives list
        to identify which polygons belong to this surface."""
    def __init__(self, first, material):
        # first refers to initial index of triangles parsed
        # count refers to number of triangles parsed
        self.first = first
        self.count = 0
        self.material_name = material
    def is_empty(self):
        return self.count == 0

class Shape(object):
    """Represents a shape (a.k.a. object) as parsed from the .obj file into .json format

        Contains a dictionary of names -> surfaces."""
    # NB: Do not pass in Null for the surfaces parameter, all shapes are assumed to
    #     contain a dictionary with at least one surface, even if it is a default one.
    def __init__(self, surfaces):
        # Dictionary of names -> surfaces
        self.surfaces = surfaces
    def is_empty(self):
        empty = True
        for surface in self.surfaces.itervalues():
            # If a single surface is non-empty, empty will be false
            empty = empty and surface.is_empty()
        return empty
    def purge_empty(self):
        purge_empty(self.surfaces)

#######################################################################################################################

# pylint: disable=R0904
class Obj2json(Mesh):
    """Parse a OBJ file and generate a Turbulenz JSON geometry asset."""
    # TODO: Probably some more information should be moved from the Obj2json class to the Shape class.

    def __init__(self, obj_file_name):
        self.default_shape_name = obj_file_name or 'initial_shape'
        self.default_surface_name = 'initial_surface'
        self.default_material_name = 'default'

        # Name of the shape/surface/material from the most recently parsed 'o'/'g'/'usemtl' line respectively
        self.curr_shape_name = self.default_shape_name
        self.curr_surf_name = self.default_surface_name
        self.curr_mtl_name = self.default_material_name

        # To keep of track of number of polygons parsed so far
        self.next_polygon_index = 0
        # A tuple of indices per vertex element
        self.indices = [ ]

        # Shortcut to be able to access the current surface in fewer characters and lookups
        self.curr_surf = Surface(0, self.default_material_name)
        # Dictionary of names -> shapes. Initialise to a default shape with a default surface
        self.shapes = { self.default_shape_name : Shape({ self.default_surface_name : self.curr_surf }) }
        Mesh.__init__(self)

    def __read_object_name(self, data):
        """Parse the 'o' line. This line contains the mesh name."""
        LOG.debug("object name:%s", data)
        # Remove any shapes with no surfaces (e.g. the default shape if a named one is given)
        purge_empty(self.shapes)
        # If a shape with this name has already been declared, do not change it,
        # append the following faces to the current shape in stead
        if data not in self.shapes:
            self.curr_shape_name = data
            self.curr_surf = Surface(self.next_polygon_index, self.curr_mtl_name)
            self.shapes[data] = Shape({self.curr_surf_name : self.curr_surf})

    def __read_group_name(self, data):
        """Parse the 'g' line. This indicates the start of a group (surface)."""
        # Remove leading/trailing whitespace
        data = data.strip()
        LOG.debug("group name:%s", data)
        # Note: Don't purge empty shapes/surfaces here, you might remove a new surface
        #       created by a preceding 'usemtl' line. Purging happens after parsing.
        self.curr_surf_name = data
        # Use most recently specified material (unless overridden later)
        self.curr_surf = Surface(self.next_polygon_index, self.curr_mtl_name)
        self.shapes[self.curr_shape_name].surfaces[data] = self.curr_surf

    def __read_material(self, data):
        """Parse the 'usemtl' line. This references a material."""
        data = data.strip()
        LOG.debug("material name:%s", data)
        self.curr_mtl_name = data
        if self.curr_surf.is_empty():
            # No polygons (yet) in the current surface, so just set its material
            self.curr_surf.material_name = data
        elif self.curr_surf.material_name != data:
            # Current surface already has a number of faces of a different material
            # so create a new surface for this new material
            self.curr_surf = Surface(self.next_polygon_index, data)
            self.curr_surf_name = _increment_name(self.curr_surf_name)
            self.shapes[self.curr_shape_name].surfaces[self.curr_surf_name] = self.curr_surf

    def __read_vertex_position(self, data):
        """Parse the 'v' line. This line contains the vertex position."""
        sv = data.split(' ')
        position = (float(sv[0]), float(sv[1]), float(sv[2]))
        self.positions.append(position)
        # Do not calculate the bounding box here, as some unused vertices may later be removed

    def __read_vertex_uvs(self, data):
        """Parse the 'vt' line. This line contains the vertex uvs."""
        # Texture coordinates
        sv = data.split(' ')
        if len(sv) == 2:
            uvs = (float(sv[0]), float(sv[1]))
        else:
            uvs = (float(sv[0]), float(sv[1]), float(sv[2]))
        self.uvs[0].append(uvs)

    def __read_vertex_normal(self, data):
        """Parse the 'vn' line. This line contains the vertex normals."""
        (sv0, sv1, sv2) = data.split(' ')
        normal = (float(sv0), float(sv1), -float(sv2))
        self.normals.append(normal)

    def __read_face(self, data):
        """Parse the 'f' line. This line contains a face.

            Constructs a tri-fan if face has more than 3 edges."""
        def __extract_indices(si):
            """Add a tuple of indices."""
            # Vertex index / Texture index / Normal index
            # Subtract 1 to count indices from 0, not from 1.
            s = si.split('/')
            if len(s) == 1:
                return [int(s[0]) - 1]
            if len(s) == 2:
                return (int(s[0]) - 1, int(s[1]) - 1)
            else:
                if len(s[1]) == 0:
                    return (int(s[0]) - 1, int(s[2]) - 1)
                else:
                    return (int(s[0]) - 1, int(s[1]) - 1, int(s[2]) - 1)

        # Split string into list of vertices
        si = data.split()
        indices = self.indices
        # Construct a tri-fan of all the vertices supplied (no support for quadrilaterals or polygons)
        # Origin vertex of fan
        i0 = __extract_indices(si[0])
        prevInd = __extract_indices(si[1])
        for i in xrange(2, len(si)):
            currInd = __extract_indices(si[i])
            indices.append(i0)
            indices.append(prevInd)
            indices.append(currInd)
            prevInd = currInd
        num_triangles = len(si) - 2
        self.next_polygon_index += num_triangles
        self.curr_surf.count += num_triangles

    def __ignore_comments(self, data):
        """Ignore comments."""

#######################################################################################################################

    def parse(self, f, prefix = ""):
        """Parse an OBJ file stream."""
        chunks_with_data = { 'v': Obj2json.__read_vertex_position,
                             'vt': Obj2json.__read_vertex_uvs,
                             'vn': Obj2json.__read_vertex_normal,
                             'f': Obj2json.__read_face,
                             'o': Obj2json.__read_object_name,
                             'g': Obj2json.__read_group_name,
                             'usemtl': Obj2json.__read_material,
                             '#': Obj2json.__ignore_comments}
        for lineNumber, line in enumerate(f):
            # The middle of the tuple is just whitespace
            (command, _, data) = line.partition(' ')
            if len(data) > 0:
                data = data[:-1]
                while len(data) > 0 and data[0] == ' ':
                    data = data[1:]
                if len(data) > 0:
                    # After stripping away excess whitespace
                    address_string = "(%d) %s%s" % (lineNumber, prefix, command)
                    if command in chunks_with_data:
                        LOG.debug(address_string)
                        # Parse data depending on its type
                        chunks_with_data[command](self, data)
                    else:
                        LOG.warning(address_string + " *unsupported*")

    def unpack_vertices(self):
        """Unpack the vertices."""
        # Consecutive list of nodes making up faces (specifically, triangles)
        indices = []

        num_components = 1
        if 0 < len(self.uvs[0]):
            num_components += 1
        if 0 < len(self.normals):
            num_components += 1

        # A node of a face definition consists of a vertex index, and optional
        # texture coord index and an optional normal vector index
        # Thus, the length of an element of self.indices can be 1, 2 or 3.
        if num_components == 1:
            # No texture coordinates (uv) or normal vector specified.
            indices = [x[0] for x in self.indices]
        else:
            old_positions = self.positions
            old_uvs = self.uvs[0]
            old_normals = self.normals
            positions = []  # Vertex position
            uvs = []        # Texture coordinate
            normals = []
            mapping = {}
            if num_components == 2:
                for indx in self.indices:
                    i0 = indx[0]
                    if len(indx) >= 2:
                        i1 = indx[1]
                    else:
                        i1 = 0
                    hash_string = "%x:%x" % (i0, i1)
                    if hash_string in mapping:
                        indices.append(mapping[hash_string])
                    else:
                        newindx = len(positions)
                        mapping[hash_string] = newindx
                        indices.append(newindx)
                        positions.append(old_positions[i0])
                        # Figure out whether 2nd value is uv or normal
                        if len(old_uvs) != 0:
                            uvs.append(old_uvs[i1])
                        else:
                            normals.append(old_normals[i1])
            else:
                for indx in self.indices:
                    i0 = indx[0]
                    if len(indx) >= 2:
                        i1 = indx[1]
                    else:
                        i1 = 0
                    if len(indx) >= 3:
                        i2 = indx[2]
                    else:
                        i2 = 0
                    hash_string = "%x:%x:%x" % (i0, i1, i2)
                    if hash_string in mapping:
                        indices.append(mapping[hash_string])
                    else:
                        newindx = len(positions)
                        mapping[hash_string] = newindx
                        indices.append(newindx)
                        positions.append(old_positions[i0])
                        uvs.append(old_uvs[i1])
                        normals.append(old_normals[i2])
            # Reassign the vertex positions, texture coordinates and normals, so
            # that they coincide with the indices defining the triangles.
            self.positions = positions
            self.uvs[0] = uvs
            self.normals = normals
        self.generate_primitives(indices)

    def extract_nbt_options(self, definitions_asset):
        """Returns whether normals and tangents/binormals are needed, and whether they should be generated.

            Loops over each material and checks their meta attributes to extract this information."""
        # Record the whether normals/tangents need to be generated, and which shapes require these options
        generate_normals  = False
        generate_tangents = False
        need_normals      = set()
        need_tangents     = set()
        for shape_name in self.shapes.iterkeys():
            for surface_name in self.shapes[shape_name].surfaces.iterkeys():
                material_name = self.shapes[shape_name].surfaces[surface_name].material_name
                material = definitions_asset.retrieve_material(material_name, default = True)
                effect = definitions_asset.retrieve_effect(material['effect'])

                # Rules used: Generating tangents implies needing tangents
                #             Needing tangents implies needing normals
                #             Needing tangents/normals implies generating them if they aren't present
                if material.meta('generate_tangents') or effect is not None and effect.meta('generate_tangents'):
                    generate_tangents = True
                    need_tangents.add(shape_name)
                elif material.meta('tangents') or effect is not None and effect.meta('tangents'):
                    need_tangents.add(shape_name)
                    # Generate tangents if any material needs tangents and you haven't parsed any,
                    # or if any materials ask you to generate tangents
                    generate_tangents = generate_tangents or not len(self.tangents) or not len(self.binormals)
                if material.meta('generate_normals') or effect is not None and effect.meta('generate_normals'):
                    generate_normals = True
                    need_normals.add(shape_name)
                elif material.meta('normals') or effect is not None and effect.meta('normals'):
                    need_normals.add(shape_name)
                    # Same reasoning as with generating tangents
                    generate_normals = generate_normals or not len(self.normals)
        if generate_tangents and 0 == len(self.uvs[0]):
            LOG.debug("Can't generate nbts without uvs:%i", len(self.uvs[0]))
            generate_tangents = False
            need_tangents     = set()
        return (need_normals, generate_normals, need_tangents, generate_tangents)
# pylint: enable=R0904

#######################################################################################################################

def parse(input_filename="default.obj", output_filename="default.json", asset_url="", asset_root=".",
          infiles=None, options=None):
    """Utility function to convert an OBJ file into a JSON file."""
    definitions_asset = standard_include(infiles)
    with open(input_filename, 'r') as source:
        asset = Obj2json(basename(input_filename))
        asset.parse(source)
        # Remove any and all unused (e.g. default) shapes and surfaces
        purge_empty(asset.shapes, recurseOnce = True)
        # Generate primitives
        asset.unpack_vertices()
        # Remove any degenerate primitives unless they're requested to be kept
        keep_degenerates = True
        for shape in asset.shapes:
            for _, surface in asset.shapes[shape].surfaces.iteritems():
                material = definitions_asset.retrieve_material(surface.material_name)
                if material.meta('keep_degenerates'):
                    keep_degenerates = True
        if not keep_degenerates:
            asset.remove_degenerate_primitives()
        # Remove any unused vertices and calculate a bounding box
        asset.remove_redundant_vertexes()
        asset.generate_bbox()
        # Generate normals/tangents if required
        (need_normals, generate_normals,
         need_tangents, generate_tangents) = asset.extract_nbt_options(definitions_asset)
        if generate_tangents:
            if generate_normals:
                asset.generate_normals()
            asset.generate_smooth_nbts()
            asset.invert_v_texture_map()
        elif generate_normals:
            asset.generate_normals()
            asset.smooth_normals()
        json_asset = JsonAsset()
        for shape_name in asset.shapes.iterkeys():
            json_asset.attach_shape(shape_name)
            node_name = NodeName("node-%s" % shape_name)
            json_asset.attach_node(node_name)
            #TODO: Should the following be divided into separate shapes?
            json_asset.attach_positions(asset.positions, shape_name)
            # Attach texture map, normals and tangents/binormals if required
            if len(asset.uvs[0]) != 0:
                json_asset.attach_uvs(asset.uvs[0], shape_name)
            if shape_name in need_tangents:
                if len(asset.tangents):
                    # Needing tangents implies needing normals and binormals
                    json_asset.attach_nbts(asset.normals, asset.tangents, asset.binormals, shape_name)
                else:
                    LOG.error('tangents requested for shape %s, but no tangents or uvs available!', shape_name)
            elif shape_name in need_normals:
                json_asset.attach_normals(asset.normals, shape_name)
            for surface_name, surface in asset.shapes[shape_name].surfaces.iteritems():
                material = definitions_asset.retrieve_material(surface.material_name)
                effect = material.get('effect', DEFAULT_EFFECT_NAME)
                effect_name = "effect-%s" % shape_name
                material_name = "material-%s" % surface.material_name
                instance_name = "instance-%s-%s" % (shape_name, surface_name)
                json_asset.attach_effect(effect_name, effect)
                mat_params = material.get('parameters', None)
                json_asset.attach_material(material_name, effect=effect, parameters=mat_params)
                def textures(mat_params):
                    for k, v in mat_params.iteritems():
                        # If a paramater of a material has a string value, it is assumed to be a texture definition
                        if isinstance(v, basestring):
                            # Return the type of the texture (e.g. 'diffuse')
                            yield k
                for t_type in textures(mat_params):
                    json_asset.attach_texture(material_name, t_type, mat_params[t_type])
                first = surface.first
                last = first + surface.count
                json_asset.attach_surface(asset.primitives[first:last], JsonAsset.SurfaceTriangles,
                                          shape_name, name=surface_name)
                json_asset.attach_node_shape_instance(node_name, instance_name, shape_name,
                                                      material_name, surface=surface_name)
        json_asset.attach_bbox(asset.bbox)
        standard_json_out(json_asset, output_filename, options)
        return json_asset

if __name__ == "__main__":
    standard_main(parse, __version__,
                  "Convert LightWave (.obj) OBJ2 files into a Turbulenz JSON asset. Supports generating NBTs.",
                  __dependencies__)
