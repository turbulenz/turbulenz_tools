#!/usr/bin/python
# Copyright (c) 2010-2011,2013 Turbulenz Limited
"""
Convert Effect Yaml (.effect) files into a Turbulenz JSON asset.
"""

import logging
LOG = logging.getLogger('asset')

import yaml

# pylint: disable=W0403
from stdtool import standard_main, standard_json_out
from asset2json import JsonAsset
# pylint: enable=W0403

__version__ = '1.0.0'
__dependencies__ = ['asset2json']

#######################################################################################################################

def parse(input_filename="default.effect", output_filename="default.json", asset_url="", asset_root=".", infiles=None,
          options=None):
    """
    Untility function to convert a Effect Yaml (.effect) into a JSON file.
    Known built-in textures are: default, quadratic, white, nofalloff, black, flat
    """
    try:
        with open(input_filename, 'r') as source:
            try:
                effects = yaml.load(source)
            # pylint: disable=E1101
            except yaml.scanner.ScannerError as e:
            # pylint: enable=E1101
                LOG.error('Failed processing: %s', input_filename)
                LOG.error('  >> %s', e)
            else:
                json_asset = JsonAsset()
                for effect_name, effect_parameters in effects.iteritems():
                    effect_type = effect_parameters.pop('type', None)
                    shader = effect_parameters.pop('shader', None)
                    meta = effect_parameters.pop('meta', None)
                    json_asset.attach_effect(effect_name, effect_type, effect_parameters, shader, meta)

                standard_json_out(json_asset, output_filename, options)
                return json_asset
    except IOError as e:
        LOG.error('Failed processing: %s', output_filename)
        LOG.error('  >> %s', e)
        return None

if __name__ == "__main__":
    try:
        standard_main(parse, __version__,
                      "Convert Effect Yaml (.effect) files into a Turbulenz JSON asset.",
                      __dependencies__)
    # pylint: disable=W0703
    except Exception as err:
        LOG.critical('Unexpected exception: %s', err)
        exit(1)
    # pylint: enable=W0703
