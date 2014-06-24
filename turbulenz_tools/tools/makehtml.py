#!/usr/bin/env python
# Copyright (c) 2012-2014 Turbulenz Limited

# Catch "Exception"
# pylint:disable=W0703

from logging import getLogger
from os.path import splitext, basename

from optparse import OptionParser, TitledHelpFormatter

from turbulenz_tools.utils.dependencies import find_dependencies
from turbulenz_tools.utils.dependencies import find_file_in_dirs
from turbulenz_tools.utils.profiler import Profiler

from turbulenz_tools.tools.templates import env_create
from turbulenz_tools.tools.templates import env_load_template
from turbulenz_tools.tools.templates import env_load_templates

from turbulenz_tools.tools.appcodegen import render_js
from turbulenz_tools.tools.appcodegen import context_from_options
from turbulenz_tools.tools.appcodegen import default_add_code
from turbulenz_tools.tools.appcodegen import inject_js_from_options
from turbulenz_tools.tools.appcodegen import default_parser_options
from turbulenz_tools.tools.appcodegen import DEFAULT_HTML_TEMPLATE
from turbulenz_tools.tools.appcodegen import output_dependency_info

from turbulenz_tools.tools.toolsexception import ToolsException
from turbulenz_tools.tools.stdtool import simple_options

__version__ = '1.8.0'
__dependencies__ = ['turbulenz_tools.utils.dependencies', 'turbulenz_tools.tools.appcodegen']

LOG = getLogger(__name__)

############################################################

def _parser():
    parser = OptionParser(description='Generate HTML files from .html and '
                          '.js files. Any options not recognised are '
                          'assumed to be input files.',
                          usage="usage: %prog [options] <input files>",
                          formatter=TitledHelpFormatter())

    default_parser_options(parser)

    parser.add_option("-C", "--code", action="store", dest="codefile",
                      help="release file to be called by the HTML. Does not "
                      "need to exist yet. (release and canvas modes only)")

    # Mode one of [ 'plugin', 'plugin-debug', 'canvas', 'canvas-debug' ]
    parser.add_option("-m", "--mode", action="store", dest="mode",
                      default='plugin-debug',
                      help="build mode: canvas, canvas-debug, plugin, "
                      "plugin-debug (default)")

    parser.add_option("-D", "--dump-default-template", action="store_true",
                      dest="dump_default_template", default=False,
                      help="output the default template to file")

    return parser

############################################################

# TODO : Move into utils
def check_input(input_files):
    """
    Divide up a list of input files into .js and .html files
    """
    js_files = []
    html_files = []
    for f in input_files:
        ext = splitext(f)[1]
        if ext in [ '.js', '.jsinc' ]:
            js_files.append(f)
        elif ext in [ '.html', '.htm' ]:
            html_files.append(f)
        else:
            LOG.error("unrecognised file type: %s", f)
            exit(1)

    return (js_files, html_files)

def load_html_template(env, input_html):
    if 1 == len(input_html):
        return env_load_template(env, input_html[0])

    return env.from_string(DEFAULT_HTML_TEMPLATE)

def dump_default_template(outfile_name):
    if outfile_name is None:
        outfile_name = 'default_template.html'

    with open(outfile_name, "wb") as f:
        f.write(DEFAULT_HTML_TEMPLATE)
    LOG.info("Default template written to: %s", outfile_name)
    return 0

def html_dump_dependencies(env, options, input_js, input_html):
    """
    Dump the dependencies of the html file being output
    """

    # For html, dependencies are:
    # - dev: html template deps, top-level js files
    # - release: html template deps
    # - canvas_dev: html template deps, top-level js files
    # - canvas: html template deps

    outfile_name = options.dependency_file
    if outfile_name is None:
        LOG.error("No dependency output file specified")
        return 1

    # Collect html dependencies (if there are html files available)

    if 1 == len(input_html):
        try:
            deps = find_dependencies(input_html[0], options.templatedirs, env,
                                     [ 'default' ])
        except Exception, e:
            raise ToolsException("dependency error: %s" % str(e))
    else:
        deps = []

    # Collect js dependencies if necessary

    if options.mode in [ 'plugin-debug', 'canvas-debug' ]:
        deps += [ find_file_in_dirs(js, options.templatedirs) for js in input_js ]

    # Write dependency info

    output_dependency_info(outfile_name, options.output, deps)

    return 0

def html_generate(env, options, input_js, input_html):
    """
    Generate html based on the templates and build mode.
    """

    # - dev, canvas_dev:
    #     render top-level js files into a temporary file
    #     collect the .js files that need to be included
    #     setup includes, startup code and the js render result into variables
    #     render html template
    #
    # - release, canvas:
    #     need to know name of output js file
    #     setup startup code to point to .tzjs or .js file
    #     render html template

    # Load templates (using default html template if not specified)

    Profiler.start('load_templates')

    template_html = load_html_template(env, input_html)
    if template_html is None:
        LOG.error("failed to load file %s from template dirs", input_html[0])
        exit(1)

    # Get context

    if len(input_js) > 0:
        title = input_js[0]
    elif options.codefile:
        title = options.codefile
    elif len(input_html) > 0:
        title = input_html[0]
    else:
        title = "Unknown"
    title = splitext(basename(title))[0]

    context = context_from_options(options, title)

    Profiler.stop('load_templates')
    Profiler.start('code_gen')

    # In development modes, render the JS code that needs embedding

    rendered_js = ""
    inc_js = []

    if options.mode in [ 'plugin-debug', 'canvas-debug' ]:
        inject_js = inject_js_from_options(options)

        Profiler.start('load_js_templates')
        templates_js = env_load_templates(env, input_js)
        Profiler.stop('load_js_templates')

        (rendered_js, inc_js) = render_js(context, options, templates_js,
                                          inject_js)

    # Add the HTML and JS code into the tz_* variables

    default_add_code(options, context, rendered_js, inc_js)

    Profiler.stop('code_gen')
    Profiler.start('html_render')

    # Render the template and write it out

    try:
        res = template_html.render(context)
    except Exception, e:
        raise ToolsException("Error in '%s': %s %s" \
                                 % (input_html, e.__class__.__name__, str(e)))

    try:
        with open(options.output, "wb") as f:
            f.write(res.encode('utf-8'))
    except IOError:
        raise ToolsException("failed to create file: %s" % options.output)

    Profiler.stop('html_render')

    return 0

############################################################

def main():

    (options, args, parser) = simple_options(_parser, __version__,
                                             __dependencies__, input_required=False)

    Profiler.start('main')
    Profiler.start('startup')

    input_files = args

    # Check that if dump-default-template is set then output and exit

    if options.dump_default_template:
        exit(dump_default_template(options.output))
    elif 0 == len(args):
        LOG.error('No input files specified')
        parser.print_help()
        exit(1)

    LOG.info("options: %s", options)
    LOG.info("args: %s", args)
    LOG.info("parser: %s", parser)
    LOG.info("templatedirs: %s", options.templatedirs)

    if options.output is None:
        LOG.error("no output file specified (required in dependency mode)")
        parser.print_help()
        exit(1)

    # Check mode

    if options.mode not in [ 'plugin-debug', 'plugin', 'canvas-debug', 'canvas' ]:
        LOG.error('Unrecognised mode: %s', options.mode)
        parser.print_help()
        exit(1)

    # Check a release source name is given if mode is one of release
    # or canvas

    if options.mode in [ 'plugin', 'canvas' ] and \
            not options.dependency and \
            not options.codefile:
        LOG.error('Missing code file name.  Use --code to specify.')
        parser.print_usage()
        exit(1)

    # Check input files and split them into (ordered) js and html

    (input_js, input_html) = check_input(input_files)

    LOG.info("js files: %s", input_js)
    LOG.info("html files: %s", input_html)

    # In debug and canvas-debug we need a .js input file

    if 0 == len(input_js):
        if options.mode in [ 'debug', 'canvas-debug' ]:
            LOG.error('Missing input .js file')
            parser.print_usage()
            exit(1)
    if 1 < len(input_html):
        LOG.error('Multiple html files specified: %s', input_html)
        exit(1)

    # Create a jinja2 env

    env = env_create(options, DEFAULT_HTML_TEMPLATE)

    Profiler.stop('startup')
    Profiler.start('run')

    # Execute

    retval = 1
    try:

        if options.dependency:
            LOG.info("generating dependencies")
            retval = html_dump_dependencies(env, options, input_js, input_html)
            LOG.info("done generating dependencies")

        else:
            retval = html_generate(env, options, input_js, input_html)

    except ToolsException, e:
        #traceback.print_exc()
        LOG.error("%s", str(e))

    Profiler.stop('run')
    Profiler.stop('main')
    Profiler.dump_data()

    return retval

############################################################

if __name__ == "__main__":
    exit(main())
