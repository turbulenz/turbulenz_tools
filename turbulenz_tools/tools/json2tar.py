#!/usr/bin/env python
# Copyright (c) 2010-2013 Turbulenz Limited

import logging
import os
import tarfile
import simplejson as json

from optparse import OptionParser, TitledHelpFormatter

from turbulenz_tools.tools.stdtool import simple_options

__version__ = '1.0.0'
__dependencies__ = [ ]

LOG = logging.getLogger(__name__)

class DependencyTar(object):
    def __init__(self):
        self.paths = [ ]

    def items(self):
        return self.paths

    def add(self, path, name_):
        self.paths.append(path)

    def close(self):
        pass

def images_in_asset(json_asset):
    """Iterator for all images used in a json asset."""
    images = json_asset.get('images', None)
    if images is not None:
        for _, image in images.iteritems():
            yield image, None

    materials = json_asset.get('materials', None)
    if materials is not None:
        texture_maps = { }
        for _, material in materials.iteritems():
            parameters = material.get('parameters', None)
            if parameters is not None:
                for texture_stage, texture_map in parameters.iteritems():
                    if isinstance(texture_map, (str, unicode)):
                        texture_maps[texture_stage] = True
                        yield texture_map, texture_stage
        LOG.info('contains: %s', ', '.join(texture_maps.keys()))

def _parser():
    parser = OptionParser(description='Generate a TAR file for binary assets referenced from a JSON asset.',
                          usage='%prog -i input.json -o output.tar [options]',
                          formatter=TitledHelpFormatter())
    parser.add_option("--version", action="store_true", dest="output_version", default=False,
                      help="output version number")
    parser.add_option("-v", "--verbose", action="store_true", dest="verbose", default=False, help="verbose output")
    parser.add_option("-s", "--silent", action="store_true", dest="silent", default=False, help="silent running")

    parser.add_option("-i", "--input", action="store", dest="input", help="input file to process")
    parser.add_option("-o", "--output", action="store", dest="output", help="output file to process")
    parser.add_option("-a", "--assets", action="store", dest="asset_root", default=".", metavar="PATH",
                      help="path of the asset root")

    parser.add_option("-M", action="store_true", dest="dependency", default=False, help="output dependencies")
    parser.add_option("--MF", action="store", dest="dependency_file", help="dependencies output to file")

    return parser

def main():
    (options, args_, parser_) = simple_options(_parser, __version__, __dependencies__)

    # Cleanly handle asset location
    asset_root = options.asset_root.replace('\\', '/').rstrip('/')

    def _filename(filename):
        if filename[0] == '/':
            return asset_root + filename
        else:
            return asset_root + '/' + filename

    tar_file = DependencyTar()

    LOG.info('%s %s', __file__, options.input)
    LOG.info('input: %s', options.input)

    try:
        with open(options.input, 'r') as source:
            json_asset = json.load(source)
            if not options.dependency:
                tar_file = tarfile.open(options.output, 'w')
            image_map = { }
            (added, missed, skipped) = (0, 0, 0)
            for image_name, texture_stage_ in images_in_asset(json_asset):
                # This is probably a procedural image - skip it
                if image_name not in image_map:
                    # We used to convert .tga -> .png, .cubemap -> .dds, and support dropping mips from dds files.
                    # Currently this is disabled until we integrate the tool with a build process.
                    # Alternatively we expect this conversion to happen in the image pipeline.
                    try:
                        image_path = _filename(image_name)
                        if os.path.exists(image_path):
                            # Actually do the tar add
                            tar_file.add(image_path, image_name)
                            LOG.info('adding: %s', image_name)
                            image_path = image_path.replace("\\", "/")
                            added += 1
                        else:
                            # We don't mind if files are missing
                            LOG.warning('missing: %s', image_name)
                            missed += 1
                    except OSError:
                        # We don't mind if files are missing
                        LOG.warning('missing: %s', image_name)
                        missed += 1
                    image_map[image_name] = 0
                else:
                    LOG.info('skipping: %s', image_name)
                    skipped += 1
                image_map[image_name] += 1
            tar_file.close()
            LOG.info('output: %s', options.output)
            LOG.info('report: added %i, missing %i, skipped %i', added, missed, skipped)
    except IOError as e:
        LOG.error(e)
        return e.errno
    except Exception as e:
        LOG.critical('Unexpected exception: %s', e)
        return 1

    if options.dependency:
        if options.dependency_file:
            LOG.info('writing dependencies: %s', options.dependency_file)
            dep_file = open(options.dependency_file, 'w')

            for dep in tar_file.items():
                dep_file.write("%s\n" % dep)
            dep_file.close()
        else:
            for dep in tar_file.items():
                print dep
            print

    return 0

if __name__ == "__main__":
    exit(main())
