# Copyright (c) 2009-2013 Turbulenz Limited
"""
Asset class used to build Turbulenz JSON assets.
"""

import logging
LOG = logging.getLogger('asset')

from itertools import chain as itertools_chain
from simplejson import encoder as json_encoder, dumps as json_dumps, dump as json_dump
from types import StringType

# pylint: disable=W0403
import vmath

from turbulenz_tools.utils.json_utils import float_to_string, metrics
from node import NodeName
from material import Material
# pylint: enable=W0403

__version__ = '1.2.0'
__dependencies__ = ['vmath', 'json2json', 'node', 'material']

#######################################################################################################################

def attach_skins_and_materials(asset, definitions, material_name, default=True):
    """Find all skins in the ``definitions`` asset which remap the material ``material_name``. Attach the found skin
    and references materials to the target ``asset``."""
    skins = definitions.retrieve_skins()
    for skin, materials in skins.iteritems():
        attach_skin = False
        for v, k in materials.iteritems():
            if v == material_name:
                attach_skin = True
                material = definitions.retrieve_material(k, default)
                asset.attach_material(k, raw=material)
        if attach_skin:
            asset.attach_skin(skin, materials)

def remove_unreferenced_images(asset, default=True):
    def _unreference_image(imageName):
        if type(imageName) is StringType:
            # this image is referenced so remove it from the unreferenced list
            if imageName in unreferenced_images:
                unreferenced_images.remove(imageName)

    images = asset.asset['images']
    unreferenced_images = set(asset.asset['images'].iterkeys())
    materials = asset.asset['materials']
    effects = asset.asset['effects']

    for v, _ in effects.iteritems():
        effect = asset.retrieve_effect(v)
        parameters = effect.get('parameters', None)
        if parameters:
            for value in parameters.itervalues():
                _unreference_image(value)

    for v, _ in materials.iteritems():
        material = asset.retrieve_material(v, default)
        parameters = material.get('parameters', None)
        if parameters:
            for value in parameters.itervalues():
                _unreference_image(value)

    # remove the unreferenced images
    for i in unreferenced_images:
        del images[i]

#######################################################################################################################

DEFAULT_IMAGE_FILENAME = 'default.png'
DEFAULT_EFFECT_TYPE = 'lambert'
DEFAULT_EFFECT_NAME = 'effect-0'
DEFAULT_MATERIAL_NAME = 'material-0'
DEFAULT_SHAPE_NAME = 'shape-0'
DEFAULT_SKELETON_NAME = 'skeleton-0'
DEFAULT_LIGHT_NAME = 'light-0'
DEFAULT_INSTANCE_NAME = 'instance-0'
DEFAULT_NODE_NAME = NodeName('node-0')
DEFAULT_TEXTURE_MAP_NAME = 'shape-map1'
DEFAULT_ANIMATION_NAME = 'animation-0'
DEFAULT_ENTITY_DEFINITION_NAME = 'entity_definition-0'
DEFAULT_MODEL_DEFINITION_NAME = 'model_definition-0'
DEFAULT_ENTITY_NAME = 'entity-0'
DEFAULT_PHYSICS_MATERIAL_NAME = 'physics-material-0'
DEFAULT_PHYSICS_NODE_NAME = 'physics-node-0'
DEFAULT_PHYSICS_MODEL_NAME = 'physics-model-0'
DEFAULT_SOUND_NAME = 'sound-0'
DEFAULT_SKIN_NAME = 'skin-0'
DEFAULT_PROCEDURALEFFECT_NAME = 'effect-0'
DEFAULT_APPLICATION_NAME = 'player'

# pylint: disable=R0904
class JsonAsset(object):
    """Contains a JSON asset."""
    SurfaceLines = 0
    SurfaceTriangles = 1
    SurfaceQuads = 2

    def __init__(self, up_axis='Y', v = 1, definitions=None):
        if definitions:
            self.asset = definitions
        else:
            self.asset = { 'version': v,
                           'geometries': { },
                           'skeletons': { },
                           'effects': { },
                           'materials': { },
                           'images': { },
                           'nodes': { },
                           'lights': { },
                           'entitydefinitions': { },
                           'modeldefinitions': { },
                           'entities': { },
                           'animations': { },
                           'camera_animations': { },
                           'physicsmaterials': { },
                           'physicsmodels': { },
                           'physicsnodes': { },
                           'sounds': { },
                           'proceduraleffects': { },
                           'areas': [ ],
                           'bspnodes': [ ],
                           'skins': { },
                           'strings': { },
                           'guis': { },
                           'tables': { },
                           'applications': { }
                         }
        if up_axis == 'X':
            self.default_transform = [ 0, 1, 0, -1, 0,  0, 0, 0, 1, 0, 0, 0 ]
        elif up_axis == 'Y':
            self.default_transform = [ 1, 0, 0,  0, 1,  0, 0, 0, 1, 0, 0, 0 ]
        elif up_axis == 'Z':
            self.default_transform = [ 1, 0, 0,  0, 0, -1, 0, 1, 0, 0, 0, 0 ]

    def json_to_string(self, sort=True, indent=1):
        """Convert the asset to JSON and return it as a string."""
        json_encoder.FLOAT_REPR = float_to_string
        return json_dumps(self.asset, sort_keys=sort, indent=indent)

    def json_to_file(self, target, sort=True, indent=0):
        """Convert the asset to JSON and write it to the file stream."""
        json_encoder.FLOAT_REPR = float_to_string
        if indent > 0:
            return json_dump(self.asset, target, sort_keys=sort, indent=indent)
        else:
            return json_dump(self.asset, target, sort_keys=sort, separators=(',', ':'))

    def clean(self):
        """Remove any toplevel elements which are empty."""
        for k in self.asset.keys():
            if isinstance(self.asset[k], dict) and len(self.asset[k].keys()) == 0:
                del self.asset[k]
            elif isinstance(self.asset[k], list) and len(self.asset[k]) == 0:
                del self.asset[k]

    def log_metrics(self):
        """Output the metrics to the log."""
        m = metrics(self.asset)
        keys = m.keys()
        keys.sort()
        for k in keys:
            LOG.info('json_asset:%s:%s', k, m[k])

#######################################################################################################################

    def __set_source(self, shape, name, stride, min_element=None, max_element=None, data=None):
        """Add a vertex stream source for the specified geometry shape."""
        if data is None:
            data = [ ]
        source = { 'stride': stride, 'data': data }
        if min_element is not None:
            source['min'] = min_element
        if max_element is not None:
            source['max'] = max_element
        LOG.debug("geometries:%s:sources:%s[%i]", shape, name, len(data) / stride)
        self.asset['geometries'][shape]['sources'][name] = source

    def __set_input(self, shape, element, data):
        """Add a vertex stream input for the specified geometry shape."""
        LOG.debug("geometries:%s:inputs:%s:%s offset %i", shape, element, data['source'], data['offset'])
        self.asset['geometries'][shape]['inputs'][element] = data

    def __set_shape(self, shape, key, data, name=None):
        """Add a key and data to the specified geometry shape."""
        if isinstance(data, list):
            LOG.debug("geometries:%s:%s[%i]", shape, key, len(data))
        else:
            LOG.debug("geometries:%s:%s:%i", shape, key, data)
        if name is None:
            self.asset['geometries'][shape][key] = data
        else:
            shape_asset = self.asset['geometries'][shape]
            if 'surfaces' not in shape_asset:
                shape_asset['surfaces'] = { }
            surfaces_asset = shape_asset['surfaces']
            if name not in surfaces_asset:
                surfaces_asset[name] = { }
            surface_asset = surfaces_asset[name]
            surface_asset[key] = data

    def __set_meta(self, shape, data):
        """Add the meta information to the specified geometry shape."""
        self.asset['geometries'][shape]['meta'] = data

    def __set_geometry(self, key, data):
        """Add a key and data to single geometry."""
        LOG.debug("geometries:%s:%s", key, data)
        self.asset['geometries'][key] = data

    def __set_asset(self, key, data):
        """Add a key and data to the asset."""
        LOG.debug("%s:%s", key, data)
        self.asset[key] = data

    def __attach_v1(self, shape, source, name, attribute, offset=0):
        """Attach a single value stream to the JSON representation. Also calculates the min and max range."""
        elements = [ ]
        (min_x) = source[0]
        (max_x) = source[0]
        for x in source:
            elements.append(x)
            min_x = min(x, min_x)
            max_x = max(x, max_x)
        self.__set_source(shape, name, 1, [min_x], [max_x], elements)
        self.__set_input(shape, attribute, { 'source': name, 'offset': offset })

    def __attach_v2(self, shape, source, name, attribute, offset=0):
        """Attach a Tuple[2] stream to the JSON representation. Also calculates the min and max range."""
        elements = [ ]
        (min_x, min_y) = source[0]
        (max_x, max_y) = source[0]
        for (x, y) in source:
            elements.append(x)
            elements.append(y)
            min_x = min(x, min_x)
            min_y = min(y, min_y)
            max_x = max(x, max_x)
            max_y = max(y, max_y)
        self.__set_source(shape, name, 2, [min_x, min_y], [max_x, max_y], elements)
        self.__set_input(shape, attribute, { 'source': name, 'offset': offset })

    def __attach_v3(self, shape, source, name, attribute, offset=0):
        """Attach a Tuple[3] stream to the JSON representation. Also calculates the min and max range."""
        if len(source) > 0:
            elements = [ ]
            (min_x, min_y, min_z) = source[0]
            (max_x, max_y, max_z) = source[0]
            for (x, y, z) in source:
                elements.append(x)
                elements.append(y)
                elements.append(z)
                min_x = min(x, min_x)
                min_y = min(y, min_y)
                min_z = min(z, min_z)
                max_x = max(x, max_x)
                max_y = max(y, max_y)
                max_z = max(z, max_z)
            self.__set_source(shape, name, 3, [min_x, min_y, min_z], [max_x, max_y, max_z], elements)
            self.__set_input(shape, attribute, { 'source': name, 'offset': offset })

    def __attach_v4(self, shape, source, name, attribute, offset=0):
        """Attach a Tuple[4] stream to the JSON representation. Also calculates the min and max range."""
        elements = [ ]
        (min_x, min_y, min_z, min_w) = source[0]
        (max_x, max_y, max_z, max_w) = source[0]
        for (x, y, z, w) in source:
            elements.append(x)
            elements.append(y)
            elements.append(z)
            elements.append(w)
            min_x = min(x, min_x)
            min_y = min(y, min_y)
            min_z = min(z, min_z)
            min_w = min(w, min_w)
            max_x = max(x, max_x)
            max_y = max(y, max_y)
            max_z = max(z, max_z)
            max_w = max(w, max_w)
        self.__set_source(shape, name, 4, [min_x, min_y, min_z, min_w], [max_x, max_y, max_z, max_w], elements)
        self.__set_input(shape, attribute, { 'source': name, 'offset': offset })

    def __retrieve_node(self, name):
        """Find the named node in the node hierarchy."""
        parts = name.hierarchy_names()
        node = self.asset
        for p in parts:
            if 'nodes' not in node:
                node['nodes'] = { }
            nodes = node['nodes']
            if p not in nodes:
                nodes[p] = { }
            node = nodes[p]
        return node

    def __retrieve_shape_instance(self,
                                  name=DEFAULT_NODE_NAME,
                                  shape_instance=DEFAULT_INSTANCE_NAME):
        assert(isinstance(name, NodeName))
        node = self.__retrieve_node(name)
        if 'geometryinstances' in node:
            geometry_instances = node['geometryinstances']
            if shape_instance in geometry_instances:
                instance = geometry_instances[shape_instance]
            else:
                instance = { }
                geometry_instances[shape_instance] = instance
        else:
            geometry_instances = { }
            node['geometryinstances'] = geometry_instances
            instance = { }
            geometry_instances[shape_instance] = instance
        return instance

    def __retrieve_light_instance(self,
                                  name=DEFAULT_NODE_NAME,
                                  light_instance=DEFAULT_INSTANCE_NAME):
        assert(isinstance(name, NodeName))
        node = self.__retrieve_node(name)
        if 'lightinstances' in node:
            light_instances = node['lightinstances']
            if light_instance in light_instances:
                instance = light_instances[light_instance]
            else:
                instance = { }
                light_instances[light_instance] = instance
        else:
            light_instances = { }
            node['lightinstances'] = light_instances
            instance = { }
            light_instances[light_instance] = instance
        return instance

#######################################################################################################################

    def attach_stream(self, source, shape, name, semantic, stride, offset):
        """Missing"""
        if source is not None:
            if isinstance(source[0], tuple) is False:
                self.__attach_v1(shape, source, name, semantic, offset)
            elif len(source[0]) == 2:
                self.__attach_v2(shape, source, name, semantic, offset)
            elif len(source[0]) == 3:
                self.__attach_v3(shape, source, name, semantic, offset)
            elif len(source[0]) == 4:
                self.__attach_v4(shape, source, name, semantic, offset)
        else:
            self.__set_source(shape, name, stride)
            self.__set_input(shape, semantic, { 'source': name, 'offset': offset })

    def attach_uvs(self, uvs, shape=DEFAULT_SHAPE_NAME, name=DEFAULT_TEXTURE_MAP_NAME, semantic="TEXCOORD0"):
        """Attach the vertex UVs to the JSON representation. Also calculates the min and max range."""
        if len(uvs[0]) == 2:
            self.__attach_v2(shape, uvs, name, semantic)
        elif len(uvs[0]) == 3:
            self.__attach_v3(shape, uvs, name, semantic)

    def attach_positions(self, positions, shape=DEFAULT_SHAPE_NAME, name="shape-positions", semantic="POSITION"):
        """Attach the vertex position stream to the JSON representation. Also calculates the min and max range."""
        self.__attach_v3(shape, positions, name, semantic)

    def attach_normals(self, normals, shape=DEFAULT_SHAPE_NAME, name="shape-normals", semantic="NORMAL"):
        """Attach the vertex normal stream to the JSON representation. Also calculates the min and max range."""
        self.__attach_v3(shape, normals, name, semantic)

    # pylint: disable=R0913
    def attach_nbts(self, normals, tangents, binormals, shape=DEFAULT_SHAPE_NAME,
                    normals_name="shape-normals", tangents_name="shape-tangents", binormals_name="shape-binormals",
                    normals_semantic="NORMAL", tangents_semantic="TANGENT", binormals_semantic="BINORMAL"):
        """Attach the vertex nbt streama to the JSON representation. Also calculates the min and max range."""
        self.__attach_v3(shape, normals, normals_name, normals_semantic)
        self.__attach_v3(shape, tangents, tangents_name, tangents_semantic)
        self.__attach_v3(shape, binormals, binormals_name, binormals_semantic)
    # pylint: enable=R0913

    def attach_skinning_data(self, skin_indices, skin_weights, shape=DEFAULT_SHAPE_NAME,
                             skin_indices_name="shape-skinindices", skin_indices_semantic="BLENDINDICES",
                             skin_weights_name="shape-skinweights", skin_weights_semantic="BLENDWEIGHT"):
        """Attach the vertex skinning indices and weights streams to the JSON representation.
        Also calculates the min and max range."""
        self.__attach_v4(shape,  skin_indices, skin_indices_name, skin_indices_semantic)
        self.__attach_v4(shape,  skin_weights, skin_weights_name, skin_weights_semantic)

    def attach_shape(self, shape=DEFAULT_SHAPE_NAME):
        """Attach the shapes to the JSON representation. This should be done before adding any shape streams."""
        self.__set_geometry(shape, { 'sources': { }, 'inputs':  { } })

    def attach_meta(self, meta, shape=DEFAULT_SHAPE_NAME):
        """Attach the meta information to the JSON representation of the shape."""
        self.__set_meta(shape, meta)

    def attach_surface(self, primitives, primitive_type, shape=DEFAULT_SHAPE_NAME, name=None):
        """Attach a surface to the JSON representation. Primitive type should be:
                SurfaceLines = 0
                SurfaceTriangles = 1
                SurfaceQuads = 2
        The primitives will be added to the specified `shape`.

        If a `name` is also specified then the primitives will be put into a named surfaces dictionary."""
        # Collapse the primitives down into a flat index list
        num_primitives = len(primitives)
        indices = [ ]
        for p in primitives:
            indices.extend(p)
        if 0 == len(indices):
            LOG.error('No indices for %s on %s', name, shape)
        if isinstance(indices[0], (tuple, list)):
            indices = list(itertools_chain(*indices))

        self.__set_shape(shape, 'numPrimitives', num_primitives, name)
        if primitive_type == JsonAsset.SurfaceLines:
            self.__set_shape(shape, 'lines', indices, name)
        elif primitive_type == JsonAsset.SurfaceTriangles:
            self.__set_shape(shape, 'triangles', indices, name)
        elif primitive_type == JsonAsset.SurfaceQuads:
            self.__set_shape(shape, 'quads', indices, name)
        else:
            LOG.error('Unsupported primitive type:%i', primitive_type)

    def attach_geometry_skeleton(self, shape=DEFAULT_SHAPE_NAME, skeleton=DEFAULT_SKELETON_NAME):
        """Add a skeleton for the specified geometry shape."""
        LOG.debug("geometries:%s:skeleton added:%s", shape, skeleton)
        self.asset['geometries'][shape]['skeleton'] = skeleton

    def attach_skeleton(self, skeleton, name=DEFAULT_SKELETON_NAME):
        """Add a skeleton object."""
        LOG.debug("%s:skeleton added", name)
        self.asset['skeletons'][name] = skeleton

    def attach_bbox(self, bbox):
        """Attach the bounding box to the top-level geometry of the JSON representation."""
        self.__set_asset('min', bbox['min'])
        self.__set_asset('max', bbox['max'])

    def attach_image(self, filename=DEFAULT_IMAGE_FILENAME, image_link=None):
        """Attach an image to the JSON respresentation."""
        if image_link is None:
            for image_link, image_filename in self.asset['images'].iteritems():
                if image_filename == filename:
                    return image_link
            index = len(self.asset['images'])
            image_link = "file%03i" % index
        self.asset['images'][image_link] = filename
        return image_link

    def attach_effect(self, name=DEFAULT_EFFECT_NAME, effect_type=DEFAULT_EFFECT_TYPE,
                      parameters=None, shader=None, meta=None, raw=None):
        """Attach a new effect to the JSON representation."""
        if raw:
            LOG.debug("effects:%s:elements:%i", name, len(raw.keys()))
            self.asset['effects'][name] = raw
        else:
            if parameters is None:
                parameters = { }
            if name not in self.asset['effects']:
                LOG.debug("effects:%s:type:%s", name, effect_type)
                effect = { 'type': effect_type, 'parameters': parameters }
                if shader is not None:
                    effect['shader'] = shader
                if meta is not None:
                    effect['meta'] = meta
                self.asset['effects'][name] = effect

    def attach_material(self, name=DEFAULT_MATERIAL_NAME, effect=DEFAULT_EFFECT_NAME,
                        technique=None, parameters=None, meta=None, raw=None):
        """Attach a material to the JSON representation."""
        if raw:
            if 'stages' in raw:
                num_stages = len(raw['stages'])
            else:
                num_stages = 0
            LOG.debug("materials:%s:elements:%i:stages:%i", name, len(raw.keys()), num_stages)
            self.asset['materials'][name] = raw
        else:
            LOG.debug("materials:%s:effect:%s", name, effect)
            material = { }
            if effect is not None:
                material['effect'] = effect
            if technique is not None:
                material['technique'] = technique
            if parameters is not None:
                material['parameters'] = parameters
            if meta is not None:
                material['meta'] = meta
            self.asset['materials'][name] = material

    def retrieve_effect(self, name):
        """Return a reference to an effect."""
        if 'effects' in self.asset and name in self.asset['effects']:
            return Material(self.asset['effects'][name])
        return None

    def retrieve_material(self, name=DEFAULT_MATERIAL_NAME, default=True):
        """Return a reference to a material."""
        if name in self.asset['materials']:
            return Material(self.asset['materials'][name])

        if default:
            default_material = { 'effect': 'default',
                                 'parameters': { 'diffuse': 'default' },
                                 'meta': { 'tangents': True } }
            LOG.warning("Material not found:%s", name)
            return Material(default_material)

        return None

    def attach_texture(self, material, stage, filename):
        """Attach an image and linked parameter to the effect of the JSON representation."""
        assert( material in self.asset['materials'] )
        file_link = self.attach_image(filename)
        LOG.debug("material:%s:parameters:%s:%s", material, stage, filename)
        # Override the texture definition to redirect to this new shortcut to the image
        self.asset['materials'][material]['parameters'][stage] = file_link

    def attach_node(self, name=DEFAULT_NODE_NAME, transform=None):
        """Attach a node with a transform to the JSON representation."""
        assert(isinstance(name, NodeName))
        if not transform:
            transform = self.default_transform
        node = self.__retrieve_node(name)
        LOG.debug("nodes:%s:matrix:%s", name, transform)
        if len(transform) == 16:
            transform = vmath.m43from_m44(transform)
        if not vmath.m43is_identity(transform):
            node['matrix'] = transform

    def attach_node_shape_instance(self, name=DEFAULT_NODE_NAME,
                                   shape_instance=DEFAULT_INSTANCE_NAME,
                                   shape=DEFAULT_SHAPE_NAME,
                                   material=DEFAULT_MATERIAL_NAME,
                                   surface=None,
                                   disabled=False):
        """Attach a node connecting a shape, material and transform to the JSON representation."""
        assert(isinstance(name, NodeName))
        assert(shape in self.asset['geometries'])
        LOG.debug("nodes:%s:geometry:%s", name, shape)
        if not material in self.asset['materials']:
            LOG.info("nodes:%s:referencing missing material:%s", name, material)
        else:
            LOG.debug("nodes:%s:material:%s", name, material)
        LOG.debug("nodes:%s:disabled:%s", name, disabled)
        instance = self.__retrieve_shape_instance(name, shape_instance)
        instance['geometry'] = shape
        instance['material'] = material
        if surface is not None:
            instance['surface'] = surface
        if disabled:
            instance['disabled'] = disabled

    def attach_shape_instance_attributes(self,
                                         name=DEFAULT_NODE_NAME,
                                         shape_instance=DEFAULT_INSTANCE_NAME,
                                         attributes=None):
        """Copy the attributes onto the node."""
        assert(isinstance(name, NodeName))
        instance = self.__retrieve_shape_instance(name, shape_instance)

        if attributes:
            for k, v in attributes.iteritems():
                instance[k] = v

    def attach_shape_instance_material(self,
                                       name=DEFAULT_NODE_NAME,
                                       shape_instance=DEFAULT_INSTANCE_NAME,
                                       material=DEFAULT_MATERIAL_NAME):
        """Attach a node connecting a material to the JSON representation."""
        assert(isinstance(name, NodeName))
        if not material in self.asset['materials']:
            LOG.info("nodes:%s:referencing missing material:%s", name, material)
        else:
            LOG.debug("nodes:%s:material:%s", name, material)
        instance = self.__retrieve_shape_instance(name, shape_instance)
        instance['material'] = material

    def attach_node_light_instance(self, name=DEFAULT_NODE_NAME,
                                   light_instance=DEFAULT_INSTANCE_NAME,
                                   light=DEFAULT_LIGHT_NAME,
                                   disabled=False):
        """Attach a node connecting a light and transform to the JSON representation."""
        assert(isinstance(name, NodeName))
        assert(light in self.asset['lights'])
        LOG.debug("nodes:%s:light:%s", name, light)
        instance = self.__retrieve_light_instance(name, light_instance)
        instance['light'] = light
        if disabled:
            instance['disabled'] = disabled

    def attach_node_attributes(self, name=DEFAULT_NODE_NAME, attributes=None):
        """Copy the attributes onto the node."""
        assert(isinstance(name, NodeName))
        node = self.__retrieve_node(name)
        if attributes:
            for k, v in attributes.iteritems():
                node[k] = v

#######################################################################################################################

    def attach_area(self, name):
        """Attach an area targetting a node."""
        area = { 'target': name, 'portals': [ ] }
        if not name in self.asset['nodes']:
            LOG.warning("portal:%s:referencing missing node:%s", name, name)
        self.asset['areas'].append(area)

    def attach_area_portal(self, index, target_index, points):
        """Attach an area portal to the area. This contains a target area, a target node and the portal points."""
        ((min_x, min_y, min_z), (max_x, max_y, max_z)) = vmath.v3s_min_max(points)
        center = ( (max_x + min_x) / 2, (max_y + min_y) / 2, (max_z + min_z) / 2 )
        halfextents = ( (max_x - min_x) / 2, (max_y - min_y) / 2, (max_z - min_z) / 2 )
        portal = { 'area': target_index, 'points': points, 'center': center, 'halfExtents': halfextents }
        self.asset['areas'][index]['portals'].append(portal)

    def attach_bsp_tree_node(self, plane, pos, neg):
        """Attach a bsp tree node."""
        node = { 'plane':plane, 'pos':pos, 'neg':neg }
        self.asset['bspnodes'].append(node)

    def retrieve_light(self, name):
        """Return a reference to a light."""
        if 'lights' in self.asset and name in self.asset['lights']:
            return self.asset['lights'][name]
        return None

    def attach_light(self, name=DEFAULT_LIGHT_NAME, raw=None):
        """Attach a light to the JSON representation."""
        self.asset['lights'][name] = raw

#######################################################################################################################

    def attach_entity_definition(self, name=DEFAULT_ENTITY_DEFINITION_NAME, attributes=None):
        """Attach an entity definition to the JSON representation."""
        if not attributes:
            attributes = { }
        self.asset['entitydefinitions'][name] = attributes

    def attach_model_definition(self, name=DEFAULT_MODEL_DEFINITION_NAME, attributes=None):
        """Attach an model definition to the JSON representation."""
        if not attributes:
            attributes = { }
        self.asset['modeldefinitions'][name] = attributes

    def attach_entity(self, name=DEFAULT_ENTITY_NAME, attributes=None):
        """Attach an entity to the JSON representation."""
        if not attributes:
            attributes = { }
        self.asset['entities'][name] = attributes

    def attach_skin(self, name=DEFAULT_SKIN_NAME, attributes=None):
        """Attach a skin to the JSON representation."""
        if not attributes:
            attributes = { }
        self.asset['skins'][name] = attributes

    def retrieve_skins(self):
        """Return all the skins."""
        return self.asset.get('skins', { })

    def retrieve_skin(self, name=DEFAULT_SKIN_NAME):
        """Return a reference to a skin."""
        skins = self.retrieve_skins()
        if name in skins:
            skin = skins[name]
        else:
            skin = { }
        return skin

#######################################################################################################################

    def attach_animation(self, name=DEFAULT_ANIMATION_NAME, animation=None):
        """Attach an animation to the JSON representation."""
        self.asset['animations'][name] = animation

    def attach_camera_animation(self, name=DEFAULT_ANIMATION_NAME, animation=None):
        """Attach a camera animation to the JSON representation."""
        self.asset['camera_animations'][name] = animation

#######################################################################################################################

    def attach_sound(self, name=DEFAULT_SOUND_NAME, sound=None):
        """Attach a sound to the JSON representation."""
        self.asset['sounds'][name] = sound

    def attach_proceduraleffect(self, name=DEFAULT_PROCEDURALEFFECT_NAME, proceduraleffect=None):
        """Attach a proceduraleffect to the JSON representation."""
        self.asset['proceduraleffects'][name] = proceduraleffect

#######################################################################################################################

    def attach_physics_material(self, physics_material_name=DEFAULT_PHYSICS_MATERIAL_NAME,
                                      physics_material=None):
        self.asset['physicsmaterials'][physics_material_name] = physics_material

    def attach_physics_model(self, physics_model=DEFAULT_PHYSICS_MODEL_NAME,
                                   shape_name=DEFAULT_SHAPE_NAME, model=None, material=None,
                                   shape_type="mesh"):
        """Attach a physics model to the JSON representation."""
        if model is None:
            model = { 'type': "rigid",
                      'shape': shape_type,
                      'geometry': shape_name }
        if material:
            model['material'] = material
        self.asset['physicsmodels'][physics_model] = model

    def attach_physics_node(self, physics_node_name=DEFAULT_PHYSICS_NODE_NAME,
                                  physics_model=DEFAULT_PHYSICS_MODEL_NAME,
                                  node_name=DEFAULT_NODE_NAME,
                                  inline_parameters=None):
        """Attach a physics node to the JSON representation."""
        assert(isinstance(node_name, NodeName))
        physics_node = { 'body': physics_model, 'target': str(node_name) }
        if inline_parameters is not None:
            for k, v in inline_parameters.iteritems():
                physics_node[k] = v
        self.asset['physicsnodes'][physics_node_name] = physics_node

#######################################################################################################################

    def attach_strings(self, name, strings):
        """Attach a named string table."""
        self.asset['strings'][name] = strings

    def attach_guis(self, name, gui):
        """Attach a named window."""
        if name not in self.asset['guis']:
            self.asset['guis'][name] = [ ]
        self.asset['guis'][name].append(gui)

    def attach_table(self, name, table):
        """Attach a table."""
        self.asset['tables'][name] = table

    def retrieve_table(self, name):
        """Retrieve a reference to a table."""
        return self.asset['tables'][name]

    def attach_application(self, name=DEFAULT_APPLICATION_NAME, options=None):
        """Attach options for an application."""
        if options is None:
            options = { }
        self.asset['applications'][name] = options
# pylint: enable=R0904
