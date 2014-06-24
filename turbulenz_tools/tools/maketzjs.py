#!/usr/bin/env python
# Copyright (c) 2012-2014 Turbulenz Limited

from turbulenz_tools.utils.dependencies import find_dependencies
from turbulenz_tools.utils.subproc import SubProc
from turbulenz_tools.utils.profiler import Profiler
from turbulenz_tools.tools.templates import read_file_utf8
from turbulenz_tools.tools.templates import env_create
from turbulenz_tools.tools.templates import env_load_templates

from turbulenz_tools.tools.appcodegen import render_js
from turbulenz_tools.tools.appcodegen import render_js_extract_includes
from turbulenz_tools.tools.appcodegen import inject_js_from_options
from turbulenz_tools.tools.appcodegen import context_from_options
from turbulenz_tools.tools.appcodegen import default_parser_options
from turbulenz_tools.tools.appcodegen import output_dependency_info

from turbulenz_tools.tools.toolsexception import ToolsException
from turbulenz_tools.tools.stdtool import simple_options

from logging import getLogger
from os import remove
from os.path import relpath, abspath, normpath
from tempfile import NamedTemporaryFile
from optparse import OptionParser, TitledHelpFormatter

import subprocess

__version__ = '1.3.0'
__dependencies__ = ['turbulenz_tools.utils.subproc', 'turbulenz_tools.utils.dependencies',
                    'turbulenz_tools.tools.appcodegen']

LOG = getLogger(__name__)

############################################################

def _parser():
    parser = OptionParser(description='Convert a JavaScript file into a .tzjs'
                          ' or .canvas.js file. Any options not recognised are'
                          ' assumed to be input files.',
                          usage="usage: %prog [options] <input files>",
                          formatter=TitledHelpFormatter())

    default_parser_options(parser)

    # Mode one of [ 'plugin', 'canvas' ]
    parser.add_option("-m", "--mode", action="store", dest="mode",
                      default='plugin', help="build mode: canvas, "
                      "plugin(default), webworker, webworker-debug")

    parser.add_option("--ignore-input-extension", action="store_true",
                      dest="ignore_ext_check", default=False,
                      help="allow input files with an extension other than .js")

    # Compacting
    parser.add_option("-y", "--yui", action="store", dest="yui", default=None,
                      help="path to the YUI compressor, setting this enables "
                      "compacting with the YUI compressor")
    parser.add_option("-c", "--closure", action="store", dest="closure",
                      default=None, help="path to the Closure compiler, setting "
                      "this enables the compacting with the Closure compiler "
                      "(EXPERIMENTAL)")
    parser.add_option("-u", "--uglifyjs", action="store", dest="uglifyjs",
                      default=None, help="path to the UglifyJS application, "
                      "setting this enables the compacting with the UglifyJS "
                      "compiler. This option assumes node.js is executable "
                      "from the path.")
    parser.add_option("--uglify", action="store", dest="uglifyjs",
                      default=None, help="Deprecated - Please use --uglifyjs")

    # Strip-debug
    parser.add_option("--no-strip-debug", action="store_false",
                      dest="stripdebug", default=True,
                      help="don't remove calls to debug.* methods")
    parser.add_option("--strip-debug", action="store",
                      dest="stripdebugpath", default=None,
                      help="set the path to the strip-debug application")
    parser.add_option("--strip-namespace", action="append", default=[],
                      dest="stripnamespaces", help="add namespace to strip "
                      "(see strip-debug --namespace flag)")
    parser.add_option("--strip-var", action="append", dest="stripvars",
                      help="define a global bool var for static code stripping "
                      "(see strip-debug -D flag)", default=[])

    parser.add_option("--ignore-errors", action="store_true",
                      dest="ignoreerrors", default=False,
                      help="ignore any syntax errors found while parsing")

    # Line length
    parser.add_option("-l", "--line-break", action="store", type="int",
                      dest="length", default=1000, help="split line length")

    return parser

############################################################

def tzjs_dump_dependencies(env, options, input_js):
    """
    Lists all the dependencies of the .js file.  We attempt to retain
    some kind of order with the leaves of the dependency tree at the
    top of the list.
    """

    # The set of files to be injected

    injects = inject_js_from_options(options)

    LOG.info("files to inject:")
    _ = [ LOG.info(" - %s", i) for i in injects ]

    # Do a full parse with a correct context, and extract the
    # javascript includes

    context = context_from_options(options, input_js[0])

    deps = render_js_extract_includes(context, options,
                                      env_load_templates(env, input_js),
                                      injects)

    # TODO : Do we need this find_dependencies stage?  It doesn't pick
    # up any javascript tags.

    for i in input_js:
        deps += find_dependencies(i, options.templatedirs, env)

    # Write dependency data

    # LOG.info("deps are: %s" % deps)
    output_dependency_info(options.dependency_file, options.output, deps)

    return 0

############################################################

def tzjs_compact(options, infile, outfile):

    LOG.info("compacting from %s to %s", infile, outfile)

    if options.yui is not None:
        command = ['java', '-jar', options.yui,
                           '--line-break', str(options.length),
                           '--type', 'js',
                           '-o', outfile, infile]

    elif options.closure is not None:
        command = ['java', '-jar', options.closure,
                           '--js_output_file=' + outfile,
                           '--js=' + infile]

    elif options.uglifyjs is not None:
        # For nodejs on win32 we need posix style paths for the js
        # module, so convert to relative path
        uglify_rel_path = relpath(options.uglifyjs).replace('\\', '/')
        command = ['node', uglify_rel_path, '-o', outfile, infile]

    LOG.info("  CMD: %s", command)
    subproc = SubProc(command)
    error_code = subproc.time_popen()

    if 0 != error_code:
        raise ToolsException("compactor command returned error code %d: %s " \
                                 % (error_code, " ".join(command)))

############################################################

def tzjs_generate(env, options, input_js):

    # The set of files to be injected

    Profiler.start('find_inject_code')
    inject_js = inject_js_from_options(options)
    Profiler.stop('find_inject_code')

    if 0 < len(inject_js):
        LOG.info("Files to inject:")
        for i in inject_js:
            LOG.info(" - '%s'", i)

    # Create a context and render the template

    Profiler.start('load_templates')
    context = context_from_options(options, input_js[0])
    templates_js = env_load_templates(env, input_js)
    Profiler.stop('load_templates')

    Profiler.start('render_js')
    (rendered_js, inc_js) = render_js(context, options, templates_js,
                                      inject_js)
    rendered_js = rendered_js.encode('utf-8')
    Profiler.stop('render_js')

    if 0 != len(inc_js):
        raise ToolsException("internal error")

    # If required, remove all calls to 'debug.*' methods BEFORE
    # compacting

    # TODO: We write and read the files too many times.  Better to
    # write once to a temporary, keep track of the name and invoke
    # each external command on files, creating subsequent temporaries
    # as required.

    if options.stripdebug:

        strip_path = "strip-debug"
        if options.stripdebugpath:
            strip_path = normpath(abspath(options.stripdebugpath))

        LOG.info("Stripping debug method calls ...")

        # Check we can actually run strip debug, with the given path
        p = subprocess.Popen('%s -h' % strip_path, stdout=subprocess.PIPE,
                                                   stderr=subprocess.STDOUT,
                                                   shell=True)
        p.communicate()
        if p.returncode != 0:
            raise ToolsException( \
                "\n\tstrip-debug tool could not be found, check it's on your path\n"
                "\tor supply the path with --strip-debug <path>. To run maketzjs\n"
                "\twithout stripping debug code run with --no-strip-debug." )

        Profiler.start('strip_debug')

        strip_debug_flags = "-Ddebug=false"

        # Add the default flags first, in case the custom flags
        # override them.

        if options.verbose:
            strip_debug_flags += " -v"
        for s in options.stripnamespaces:
            strip_debug_flags += " --namespace %s" % s
        for v in options.stripvars:
            strip_debug_flags += " -D %s" % v
        if options.ignoreerrors:
            strip_debug_flags += " --ignore-errors"

        # Launch the strip command and pass in the full script via
        # streams.

        with NamedTemporaryFile(delete = False) as t:
            LOG.info("Writing temp JS to '%s'", t.name)
            t.write(rendered_js)

        with NamedTemporaryFile(delete = False) as tmp_out:
            pass

        strip_cmd = "%s %s -o %s %s" % (strip_path, strip_debug_flags,
                                     tmp_out.name, t.name)
        LOG.info("Strip cmd: %s", strip_cmd)
        strip_retval = subprocess.call(strip_cmd, shell=True)

        if 0 != strip_retval:
            raise ToolsException( \
                "strip-debug tool exited with code %d\n"
                "The (merged) input probably contains a syntax error:\n"
                "  %s" % (strip_retval, t.name))

        rendered_js = read_file_utf8(tmp_out.name).encode('utf-8')
        remove(tmp_out.name)
        remove(t.name)

        Profiler.stop('strip_debug')

    # If required, compact the JS via a temporary file, otherwise just
    # write out directly to the output file.

    if options.mode != 'webworker-debug' and (options.yui or options.closure or options.uglifyjs):

        Profiler.start('compact')

        with NamedTemporaryFile(delete = False) as t:
            LOG.info("Writing temp JS to '%s'", t.name)
            t.write(rendered_js)

        LOG.info("Compacting temp JS to '%s'", options.output)
        tzjs_compact(options, t.name, options.output)
        remove(t.name)
        Profiler.stop('compact')

    else:

        LOG.info("Writing JS to '%s'", options.output)
        Profiler.start('write_out')
        try:
            with open(options.output, 'wb') as f:
                f.write(rendered_js)
                LOG.info("Succeeded")
        except IOError:
            raise ToolsException("failed to write file: %s" % options.output)
        Profiler.stop('write_out')

    return 0

############################################################

def main():
    (options, args, parser) = simple_options(_parser, __version__,
                                             __dependencies__)

    Profiler.start('main')
    Profiler.start('startup')

    # Sanity checks

    if 0 == len(args):
        LOG.error("no input files specified")
        parser.print_help()
        exit(1)

    if options.mode not in [ 'plugin', 'canvas', 'webworker', 'webworker-debug' ]:
        LOG.error("invalid mode %s", options.mode)
        parser.print_help()
        exit(1)

    if options.output is None:
        LOG.error("no output file specified (required in dependency mode)")
        parser.print_help()
        exit(1)

    # Create a jinja2 env

    env = env_create(options)
    input_js = args

    LOG.info("input files: %s", input_js)

    Profiler.stop('startup')
    Profiler.start('run')

    # Execute

    retval = 1
    try:

        if options.dependency:
            LOG.info("dependency generation selected")
            retval = tzjs_dump_dependencies(env, options, input_js)
        else:
            LOG.info("rendering tzjs")
            retval = tzjs_generate(env, options, input_js)

    except ToolsException, e:
        LOG.error(str(e))
        exit(1)

    Profiler.stop('run')
    Profiler.stop('main')
    Profiler.dump_data()

    return retval

if __name__ == "__main__":
    exit(main())
