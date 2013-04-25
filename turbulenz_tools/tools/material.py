# Copyright (c) 2009-2011,2013 Turbulenz Limited
"""
Utility for manipluating Materials.
"""

__version__ = '1.0.0'

def clean_material_name(material_name):
    """Make sure the material name is consistent."""
    return material_name.lower().replace('\\', '/')

def is_material_collidable(material):
    """Check whether a material has meta suggesting we need collision meshes"""
    collision_filter = material.meta('collisionFilter')
    return (not collision_filter) or (len(collision_filter) > 0)

# pylint: disable=R0904
class Material(dict):
    """Material class to provide safe meta and parameter attribute access."""

    def __init__(self, source_material=None):
        if source_material is None:
            source_material = { }
        super(Material, self).__init__(source_material)
        for k, v in source_material.iteritems():
            if isinstance(v, dict):
                self[k] = v.copy()
            else:
                self[k] = v

    def meta(self, key):
        """Return a meta attribute. Returns None if the attribute is missing."""
        if 'meta' in self:
            if key in self['meta']:
                return self['meta'][key]
        return None

    def param(self, key, value=None):
        """Returns a parameter attribute. Returns None if the attribute is missing."""
        if value is None:
            if 'parameters' in self:
                if key in self['parameters']:
                    return self['parameters'][key]
            return None
        else:
            if 'parameters' not in self:
                self['parameters'] = { }
            self['parameters'][key] = value

    def pop_param(self, key, default=None):
        """Pop a parameter attribute."""
        params = self.get('parameters', None)
        if params:
            return params.pop(key, default)
        else:
            return default

    def remove(self, key):
        """Delete an attribute from the material."""
        if key in self:
            del(self[key])
# pylint: enable=R0904
