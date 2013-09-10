# Copyright (c) 2009-2013 Turbulenz Limited
"""
Utilities to simplify building a standard translater.
"""

import sys
import logging
LOG = logging.getLogger('asset')

from os.path import basename as path_basename, exists as path_exists
from simplejson import load as json_load
from optparse import OptionParser, OptionGroup, TitledHelpFormatter

# pylint: disable=W0403
from asset2json import JsonAsset
from turbulenz_tools.utils.json_utils import merge_dictionaries
# pylint: enable=W0403

#######################################################################################################################


#######################################################################################################################

def standard_output_version(version, dependencies, output_file=None):
    main_module_name = path_basename(sys.argv[0])
    version_string = None
    if dependencies:
        deps = { }

        def get_dependencies_set(this_module_name, deps_list):
            for module_name in deps_list:
                if module_name not in deps:
                    m = None
                    try:
                        m = __import__(module_name, globals(), locals(),
                                       ['__version__', '__dependencies__'])
                    except ImportError:
                        print "Failed to import %s, listed in dependencies " \
                            "for %s" % (module_name, this_module_name)
                        exit(1)
                    else:
                        # Test is the module actually has a version attribute
                        try:
                            version_ = m.__version__
                        except AttributeError as e:
                            print 'No __version__ attribute for tool %s' \
                                % m.__name__
                            print ' >> %s' % str(e)
                        else:
                            deps[module_name] = m

                    if m is not None:
                        try:
                            get_dependencies_set(module_name,
                                                 m.__dependencies__)
                        except AttributeError:
                            pass

        get_dependencies_set(main_module_name, dependencies)

        module_names = deps.keys()
        module_names.sort()

        module_list = ', '.join(['%s %s' % (deps[m].__name__, deps[m].__version__) for m in module_names])
        version_string = '%s %s (%s)' % (main_module_name, version, module_list)
    else:
        version_string = '%s %s' % (main_module_name, version)

    # If we are given an output file, write the versions info there if
    # either:
    #   the file doesn't exist already, or
    #   the file contains different data
    # If we are given no output file, just write to stdout.

    print version_string
    if output_file is not None:
        if path_exists(output_file):
            with open(output_file, "rb") as f:
                old_version = f.read()
            if old_version == version_string:
                return
        with open(output_file, "wb") as f:
            f.write(version_string)

def standard_include(infiles):
    """Load and merge all the ``infiles``."""
    if infiles:
        definitions = { }
        for infile in infiles:
            if path_exists(infile):
                with open(infile, 'r') as infile_file:
                    infile_json = json_load(infile_file)
                    definitions = merge_dictionaries(infile_json, definitions)
            else:
                LOG.error('Missing file: %s', infile)
        return JsonAsset(definitions=definitions)
    else:
        return JsonAsset()
    return None

def standard_parser(description, epilog=None, per_file_options=True):
    """Standard set of parser options."""
    parser = OptionParser(description=description, epilog=epilog,
                          formatter=TitledHelpFormatter())
    parser.add_option("--version", action="store_true", dest="output_version",
                      default=False, help="output version number to output "
                      "file, or stdout if no output file is given")
    parser.add_option("-v", "--verbose", action="store_true", dest="verbose",
                      default=False, help="verbose outout")
    parser.add_option("-s", "--silent", action="store_true", dest="silent",
                      default=False, help="silent running")
    if per_file_options:
        parser.add_option("-m", "--metrics", action="store_true",
                          dest="metrics", default=False, help="output asset "
                          "metrics")
    parser.add_option("--log", action="store", dest="output_log", default=None,
                      help="write log to file")

    group = OptionGroup(parser, "Asset Generation Options")
    group.add_option("-j", "--json_indent", action="store", dest="json_indent",
                     type="int", default=0, metavar="SIZE",
                     help="json output pretty printing indent size, defaults "
                     "to 0")

    # TODO - Asset Generation Options currently disabled
    #
    #group.add_option("-6", "--base64-encoding", action="store_true", dest="b64_encoding", default=False,
    #                 help=("encode long float and int attributes in base64, defaults to disabled %s" %
    #                        "- [ currently unsupported ]"))
    #group.add_option("-c", "--force-collision", action="store_true", dest="force_collision", default=False,
    #                 help="force collision generation - [ currently unsupported ]")
    #group.add_option("-r", "--force-render", action="store_true", dest="force_render", default=False,
    #                 help="force rendering generation - [ currently unsupported ]")

    group.add_option("--keep-unused-images", action="store_true", dest="keep_unused_images", default=False,
                     help="keep images with no references to them")

    group.add_option("-I", "--include-type", action="append", dest="include_types", default=None, metavar="TYPE",
                     help="only include objects of class TYPE in export.")
    group.add_option("-E", "--exclude-type", action="append", dest="exclude_types", default=None, metavar="TYPE",
                     help="exclude objects of class TYPE from export. "
                          "Classes currently supported for include and exclude: "
                          "geometries, nodes, animations, images, effects, materials, lights, "
                          "physicsmaterials, physicsmodels and physicsnodes. "
                          "CAUTION using these options can create incomplete assets which require fixup at runtime. ")
    parser.add_option_group(group)

    group = OptionGroup(parser, "Asset Location Options")
    group.add_option("-u", "--url", action="store", dest="asset_url", default="", metavar="URL",
                     help="asset URL to prefix to all asset references")
    group.add_option("-a", "--assets", action="store", dest="asset_root", default=".", metavar="PATH",
                     help="PATH of the asset root")
    group.add_option("-d", "--definitions", action="append", dest="definitions", default=None, metavar="JSON_FILE",
                     help="definition JSON_FILE to include in build, this option can be used repeatedly for multiple "
                          "files")
    parser.add_option_group(group)

    if per_file_options:
        group = OptionGroup(parser, "File Options")
        group.add_option("-i", "--input", action="store", dest="input", default=None, metavar="FILE",
                         help="source FILE to process")
        group.add_option("-o", "--output", action="store", dest="output", default="default.json", metavar="FILE",
                         help="output FILE to write to")
        parser.add_option_group(group)

    # TODO - Database Options are currently disabled
    #
    #group = OptionGroup(parser, "Database Options")
    #group.add_option("-A", "--authority", action="store", dest="authority", default=None,
    #                 metavar="HOST:PORT",
    #                 help=("Authority of the database in the form HOST:PORT. %s" %s
    #                       "If undefined, database export is disabled."))
    #group.add_option("-D", "--database", action="store", dest="database", default="default",
    #                 metavar="NAME", help="NAME of the document database")
    #group.add_option("-P", "--put-post", action="store_true", dest="put_post", default=False,
    #                 help="put or post the asset to the authority database")
    #group.add_option("-O", "--document", action="store", dest="document", default="default.asset",
    #                 metavar="NAME", help="NAME of the document")
    #parser.add_option_group(group)

    return parser

def standard_main(parse, version, description, dependencies, parser = None):
    """Provide a consistent wrapper for standalone translation.
       When parser is not supplied, standard_parser(description) is used."""

    parser = parser or standard_parser(description)
    (options, args_) = parser.parse_args()

    if options.output_version:
        standard_output_version(version, dependencies, options.output)
        return

    if options.input is None:
        parser.print_help()
        return

    if options.silent:
        logging.basicConfig(level=logging.CRITICAL, stream=sys.stdout)
    elif options.verbose or options.metrics:
        logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    else:
        logging.basicConfig(level=logging.WARNING, stream=sys.stdout)

    LOG.info("input: %s", options.input)
    LOG.info("output: %s", options.output)

    if options.asset_url != '':
        LOG.info("url: %s", options.asset_url)

    if options.asset_root != '.':
        LOG.info("root: %s", options.asset_root)

    if options.definitions:
        for inc in options.definitions:
            LOG.info("inc: %s", inc)

    # TODO - Database Options are currently disabled
    #
    #if options.put_post:
    #    LOG.info("## authority: %s" % (options.authority))

    json_asset_ = parse(options.input, options.output,
                        options.asset_url, options.asset_root, options.definitions,
                        options)

    # TODO - Database Options are currently disabled
    #
    #if options.put_post:
    #    try:
    #        from couchdbkit import Server
    #        from couchdbkit.resource import PreconditionFailed
    #        database_supported = True
    #    except ImportError:
    #        database_supported = False
    #
    #    if database_supported and json_asset and options.put_post:
    #        server_uri = 'http://' + options.authority + '/'
    #        server = Server(uri=server_uri)
    #        try:
    #            database = server.get_or_create_db(options.database)
    #        except PreconditionFailed:
    #            database = server[options.database]
    #        if database.doc_exist(options.document):
    #            pass
    #        else:
    #            database[options.document] = json_asset.asset

def standard_json_out(json_asset, output_filename, options=None):
    """Provide a consistent output of the JSON assets."""

    indent = 0
    if options is not None:
        indent = options.json_indent

    metrics = False
    if options is not None:
        metrics = options.metrics

    json_asset.clean()
    if metrics:
        json_asset.log_metrics()

    with open(output_filename, 'w') as target:
        json_asset.json_to_file(target, True, indent)
        target.write('\n')

#######################################################################################################################

def simple_options(parser_fn, version, dependencies, input_required=True):
    parser = parser_fn()
    (options, args) = parser.parse_args()

    if options.output_version:
        standard_output_version(version, dependencies, getattr(options, 'output', None))
        exit(0)

    if input_required:
        # Not all tools have an input file, so we print help for no args as well.
        try:
            if options.input is None:
                print "ERROR: no input files specified"
                parser.print_help()
                exit(1)
        except AttributeError:
            if len(args) == 0:
                print "ERROR: no input files specified"
                parser.print_help()
                exit(1)

    # Not all tools have a metrics option.
    try:
        metrics = options.metrics
    except AttributeError:
        metrics = False

    if options.silent:
        logging.basicConfig(level=logging.CRITICAL)
    elif options.verbose or metrics:
        logging.basicConfig(level=logging.INFO)
    else:
        logging.basicConfig(level=logging.WARNING)

    return (options, args, parser)
