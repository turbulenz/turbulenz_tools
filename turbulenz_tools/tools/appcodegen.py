# Copyright (c) 2012-2014 Turbulenz Limited

"""
This file contains all of the code generation, formatting and default
templates for the build tools.  This includes the set of variables
used to render the html templates, the format of dependency
information and the set of shared options across the code build tools.
"""

from turbulenz_tools.utils.dependencies import find_file_in_dirs
from turbulenz_tools.utils.profiler import Profiler
from turbulenz_tools.tools.toolsexception import ToolsException
from turbulenz_tools.tools.templates import read_file_utf8

import os.path
import glob
from re import compile as re_compile
from logging import getLogger

__version__ = '1.1.4'

LOG = getLogger(__name__)

############################################################

DEFAULT_HTML_TEMPLATE = """
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN" "http://www.w3.org/TR/html4/strict.dtd">
<html>
<head>
    <title>
        /*{% block tz_app_title %}*//*{{ tz_app_title_var }}*//*{% endblock %}*/
    </title>
    <meta http-equiv="Content-Type" content="text/html;charset=utf-8" >
    <style type="text/css">
html, body, div, span, object, iframe, h1, h2, p, a, img, ul, li, fieldset, form, label, legend, table, thead, tbody, tfoot, tr, th, td {
    border: 0;
    font-size: 100%;
    margin: 0;
    outline: 0;
    padding: 0;
    vertical-align: baseline;
}
    </style>
    <!-- block tz_app_header -->
    /*{% block tz_app_header %}*//*{% endblock %}*/
    <!-- end tz_app_header -->
</head>
<body style="background:#B4B4B4;font:normal normal normal 13px/1.231 Helvetica,Arial,sans-serif;text-shadow:1px 1px #F9F8F8;">
    <div id="titlebar" style="position:fixed;height:65px;top:0;right:0;left:0;">
        <strong style="font-size:24px;line-height:64px;margin:16px;">
            <!-- block tz_app_title_name -->
            /*{% block tz_app_title_name %}*/
            /*{{ tz_app_title_name_var }}*/
            /*{% endblock %}*/
            <!-- end tz_app_title_name -->
        </strong>
        <div id="titlelogo"
             style="float:right;width:27px;height:27px;margin:18px 24px;">
        </div>
    </div>
    <div id="sidebar"
         style="background:#B4B4B4;position:fixed;width:303px;top:65px;left:0;">
        <!-- block tz_app_html_controls -->
        /*{% block tz_app_html_controls %}*/
        /*{% endblock %}*/
        <!-- end tz_app_html_controls -->
    </div>
    <div id="engine" style="background:#939393;position:fixed;top:65px;
                            bottom:0;right:0;left:303px;
                            border-left:1px solid #898989;">
        <!--
          HTML to create a plugin or canvas instance.
          Supplied by 'tz_engine_div' variable.
        -->
        /*{{ tz_engine_div }}*/
    </div>

    <!-- begin 'tz_include_js' variable -->
    /*{{ tz_include_js }}*/
    <!-- end 'tz_include_js' variable -->

    <script type="text/javascript">
      // ----------------------------------------
      // Embedded code and startup code.
      // Supplied by 'tz_startup_code' variable.
      // ----------------------------------------
      /*{{ tz_startup_code }}*/
    </script>

</body>
</html>
"""

############################################################

def default_parser_options(parser):
    """
    Command line options shared by make*.py tools
    """

    parser.add_option("--version", action="store_true", dest="output_version",
                      default=False, help="output version number")
    parser.add_option("-v", "--verbose", action="store_true", dest="verbose",
                      default=False, help="verbose output")
    parser.add_option("-s", "--silent", action="store_true", dest="silent",
                      default=False, help="silent running")

    # Input / Output (input .html and .js files don't need a prefix)
    parser.add_option("-o", "--output", action="store", dest="output",
                      help="output file to process")
    parser.add_option("-t", "--templatedir", action="append", dest="templatedirs",
                      default=[], help="template directory (multiple allowed)")

    # Dependency generation
    parser.add_option("-M", "--dependency", action="store_true",
                      dest="dependency", default=False,
                      help="output dependencies")
    parser.add_option("--MF", action="store", dest="dependency_file",
                      help="dependencies output to file")

    # "use strict" options
    parser.add_option("--use-strict", action="store_true", dest="use_strict",
                      default=False, help='enforce "use strict"; statement. '
                      'This adds a single "use strict"; line at the top of the '
                      'JavaScript code.')
    parser.add_option("--include-use-strict", action="store_true",
                      dest="include_use_strict", default=False,
                      help='don\'t strip out "use strict"; statements. '
                      'By default all "use strict"; statements are removed '
                      'from the output file.')

    # Hybrid
    parser.add_option("--hybrid", action="store_true", dest="hybrid",
                      default=False, help="canvas, canvas_dev modes only. "
                      "Start up a plugin as well as a canvas-based "
                      "TurbulenzEngine. The plugin will be available as "
                      "TurbulenzEnginePlugin.")

    # Profiling
    def _enable_profiler(_options, _opt_str, _value, _parser):
        Profiler.enable()
    parser.add_option("--profile", action="callback", callback=_enable_profiler,
                      help="enable the collection and output of profiling "
                      "information")

    # Injecting files
    parser.add_option("--no-inject", action="store_true", dest="noinject",
                      default=False, help="Don't inject default library files")

############################################################

def render_js(context, options, templates_js, inject_js):
    """
    Renders the templates in templates_js, as if the first template
    began with include declarations for each of the files in
    inject_js.  Returns the result of rendering, and the list of
    includes that were not inlined.  (rendered_js, inc_js)

    For dev modes, the list of includes is returned in inc_js as
    relative paths from the output file.  For release modes, includes
    are all inlined (inc_js == []).
    """

    regex_use_strict = re_compile('"use strict";')

    out = []
    inc_js = []
    outfile_dir = os.path.abspath(os.path.dirname(options.output)) + os.sep

    includes_seen = []

    # Any headers

    if options.use_strict:
        out.append('"use strict";')

    if options.mode in [ 'plugin', 'canvas' ]:
        out.append('(function () {')

    # Functions for handling includes

    def _find_include_or_error(name):
        try:
            f = find_file_in_dirs(name, options.templatedirs)
        except Exception, ex:
            raise ToolsException(str(ex))
        if f is None:
            raise ToolsException("No file '%s' in any template dir" % name)
        LOG.info(" resolved '%s' to path '%s'", name, f)
        return f

    def handle_javascript_dev(name):
        file_path = _find_include_or_error(name)
        if file_path in includes_seen:
            LOG.info(" include '%s' (%s) already listed", name, file_path)
            return ""
        includes_seen.append(file_path)

        # Calculate relative path name
        # rel_path = file_path.replace(outfile_dir, '').replace('\\', '/')
        # if rel_path == file_path:
        #     raise ToolsException("Included file '%s' found at '%s', which is "
        #                          "not in a child directory of the output file "
        #                          "'%s' in directory %s" % (name, file_path,
        #                                                    options.output,
        #                                                    outfile_dir))
        rel_path = os.path.relpath(file_path, outfile_dir).replace('\\', '/')

        inc_js.append(rel_path)
        return ""

    def handle_javascript_webworker_dev(name):
        file_path = _find_include_or_error(name)
        if file_path in includes_seen:
            LOG.info(" include '%s' (%s) already listed", name, file_path)
            return ""
        includes_seen.append(file_path)

        rel_path = os.path.relpath(file_path, outfile_dir).replace('\\', '/')

        return ('importScripts("%s");' % rel_path).encode('utf-8')

    def handle_javascript_release(name):
        if options.stripdebug and os.path.basename(name) == "debug.js":
            LOG.warning("App attempting to include debug.js.  Removing.")
            return ""
        file_path = _find_include_or_error(name)
        if file_path in includes_seen:
            LOG.info(" include '%s' (%s) already listed", name, file_path)
            return ""
        includes_seen.append(file_path)

        d = read_file_utf8(file_path)

        if options.include_use_strict:
            return d
        else:
            # strip out any "use strict"; lines
            return regex_use_strict.sub('', d)

    if options.mode in [ 'plugin', 'canvas', 'webworker' ]:
        handle_javascript = handle_javascript_release
    elif options.mode == 'webworker-debug':
        handle_javascript = handle_javascript_webworker_dev
    else:
        handle_javascript = handle_javascript_dev
    context['javascript'] = handle_javascript

    # Inject any includes at the start, either embedding them or
    # adding to the inc_js list.

    for inj in inject_js:
        js_line = handle_javascript(inj)
        if js_line:
            out.append(js_line)

    # Render templates

    out += [t.render(context) for t in templates_js]
    del context['javascript']

    # Any footer code

    if options.mode == 'plugin':
        out.append("""
    if (!TurbulenzEngine.onload)
    {
        window.alert("Entry point 'TurbulenzEngine.onload' must be defined.");
        return;
    }
    TurbulenzEngine.onload.call(this);
}());""")

    if options.mode == 'canvas':
        out.append('window.TurbulenzEngine = TurbulenzEngine;}());')

    # Combine all parts into a single string

    return ("\n".join(out), inc_js)

def render_js_extract_includes(context, options, templates_js, injects):
    """
    Renders the templates in templates_js against the given context
    and just collects the set of 'javascript('...')' includes.  Will
    optionally handle a list of files to be injected.

    Returns an array of absolute paths, removing duplicates.
    """

    includes = []

    def _find_in_dirs_or_error(name):
        file_path = find_file_in_dirs(name, options.templatedirs)
        if file_path is None:
            raise ToolsException("No file '%s' in any template dir" % name)
        if file_path in includes:
            LOG.info(" include '%s' (%s) already listed", name, file_path)
            return
        LOG.info(" resolved '%s' to path '%s'", name, file_path)
        includes.append(file_path)

    # In release mode, filter out debug.js

    if options.mode in [ 'plugin', 'canvas' ] and options.stripdebug:
        _do_find_in_dirs_or_error = _find_in_dirs_or_error
        # pylint: disable=E0102
        def _find_in_dirs_or_error(name):
            if os.path.basename(name) == "debug.js":
                LOG.warning("App attempting to include debug.js.  Removing.")
                return
            _do_find_in_dirs_or_error(name)
        # pylint: enable=E0102

    # Deal with any injects

    for i in injects:
        _find_in_dirs_or_error(i)

    # Use the templating engine to deal with remaining includes

    def handle_javascipt_extract_includes(name):
        _find_in_dirs_or_error(name)
        return ""

    context['javascript'] = handle_javascipt_extract_includes

    for t in templates_js:
        t.render(context)

    del context['javascript']

    return includes

############################################################

def output_dependency_info(dependency_file, output_file, dependencies):
    """
    This dependency write outputs dependency information in a format
    consistent with the GCC -M flags.
    """

    try:
        with open(dependency_file, "wb") as f:
            f.write(output_file)
            f.write(" ")
            f.write(dependency_file)
            f.write(" : \\\n")
            for d in dependencies:
                f.write("    ")
                f.write(d)
                f.write(" \\\n")
            f.write("\n\n")
            for d in dependencies:
                f.write(d)
                f.write(" :\n\n")
    except IOError:
        raise ToolsException("failed to write file: %s" % dependency_file)

############################################################

def context_from_options(options, title):

    # Sanity check

    if options.hybrid:
        if options.mode not in [ 'canvas', 'canvas-debug' ]:
            raise ToolsException("--hybrid option available only in canvas and "
                                 "canvas_dev modes")

    # Set up the context

    context = {}
    context['tz_app_title_name_var'] = title
    context['tz_app_title_var'] = title

    context['tz_development'] = options.mode in [ 'plugin-debug', 'canvas-debug', 'webworker-debug' ]
    context['tz_canvas'] = options.mode in [ 'canvas', 'canvas-debug' ]
    context['tz_webworker'] = options.mode in [ 'webworker', 'webworker-debug' ]
    context['tz_hybrid'] = options.hybrid

    return context

############################################################

def inject_js_from_options(options):
    """
    Given the build options, find (if necessary), all includes that
    must be injected for canvas mode to work.  This is done by
    searching for webgl_engine_file in any of the
    template directories, and collecting the list of all .js files
    that reside there.
    """

    inject_list = []

    if options.noinject:
        return inject_list

    mode = options.mode

    # Put debug.js at the top (if in debug mode), and ALWAYS include
    # vmath.js

    if mode in [ 'plugin-debug', 'canvas-debug', 'webworker-debug' ] or not options.stripdebug:
        inject_list.append('jslib/debug.js')
    inject_list.append('jslib/vmath.js')

    # Include webgl includes in canvas mode

    if mode in [ 'canvas', 'canvas-debug' ]:
        LOG.info("Looking for jslib/webgl ...")

        webgl_engine_file = 'jslib/webgl/turbulenzengine.js'
        webgl_engine_dir = os.path.dirname(webgl_engine_file)

        # Find absolute path of webgl_engine_file

        webgl_abs_path = None

        for t in options.templatedirs:
            p = os.path.join(t, webgl_engine_file)
            if os.path.exists(p):
                webgl_abs_path = os.path.dirname(p)
                LOG.info("Found at: %s", webgl_abs_path)
                break

        if webgl_abs_path is None:
            raise ToolsException("No '%s' in any template dir" \
                                     % webgl_engine_file)

        webgl_abs_files = glob.glob(webgl_abs_path + "/*.js")
        inject_list += [ 'jslib/utilities.js',
                         'jslib/aabbtree.js',
                         'jslib/observer.js' ]
        inject_list += \
            [ webgl_engine_dir + "/" + os.path.basename(f) for f in webgl_abs_files ]

    return inject_list

############################################################

def default_add_code(options, context, rendered_js, inc_js):
    """
    Add:
      tz_engine_div
      tz_include_js
      tz_startup_code
    to the context, based on the values of options
    """

    # pylint: disable=W0404
    from turbulenz_tools.version import SDK_VERSION as engine_version
    # pylint: enable=W0404
    engine_version_2 = ".".join(engine_version.split(".")[0:2])

    outfile_dir = os.path.dirname(options.output)
    if options.mode in [ 'plugin', 'canvas' ]:
        codefile_rel = os.path.relpath(options.codefile, outfile_dir).replace('\\', '/')

    #
    # tz_engine_div and tz_engine_2d_div
    #

    tz_engine_div = ""
    if options.mode in [ 'canvas', 'canvas-debug' ]:

        tz_engine_div += """

        <style>#turbulenz_game_engine_canvas { -ms-touch-action: none; }</style>
        <canvas id="turbulenz_game_engine_canvas" moz-opaque="true" tabindex="1">
            Sorry, but your browser does not support WebGL or does not have it
            enabled.  To get a WebGL-enabled browser, please see:<br/>
            <a href="http://www.khronos.org/webgl/wiki/Getting_a_WebGL_Implementation" target="_blank">
                Getting a WebGL Implementation
            </a>
        </canvas>

        <script type="text/javascript">
            var canvasSupported = true;
            (function()
            {
                var contextNames = ["webgl", "experimental-webgl"];
                var context = null;
                var canvas = document.createElement('canvas');

                document.body.appendChild(canvas);

                for (var i = 0; i < contextNames.length; i += 1)
                {
                    try {
                        context = canvas.getContext(contextNames[i]);
                    } catch (e) {}

                    if (context) {
                        break;
                    }
                }
                if (!context)
                {
                    canvasSupported = false;
                    window.alert("Sorry, but your browser does not support WebGL or does not have it enabled.");
                }

                document.body.removeChild(canvas);
            }());
            var TurbulenzEngine = {};
        </script>"""

        tz_engine_2d_div = """
        <canvas id="turbulenz_game_engine_canvas" moz-opaque="true" tabindex="1">
        </canvas>

        <script type="text/javascript">
            var canvasSupported = true;
            (function()
            {
                var canvas = document.createElement("canvas");
                document.body.appendChild(canvas);
                if (!canvas.getContext("2d"))
                {
                    canvasSupported = false;
                    window.alert("Sorry, but your browser does not support 2D Canvas or does not have it enabled.");
                }
                document.body.removeChild(canvas);
            }());
            var TurbulenzEngine = {};
        </script>"""


    if options.mode in [ 'plugin', 'plugin-debug' ] or options.hybrid:

        tz_engine_div += """
        <script type="text/javascript">
            if (window.ActiveXObject)
            {
                document.write('<object id="turbulenz_game_loader_object" classid="CLSID:49AE29B1-3E7D-4f62-B3D2-D6F7C7BEE728" width="100%" height="100%">');
                document.write('<param name="type" value="application/vnd.turbulenz" \/>');
                document.write('<p>You need the Turbulenz Engine for this.');
                document.write('<\/p>');
                document.write('<\/object>');
            }
            else
            {
                // browser supports Netscape Plugin API
                document.write('<object id="turbulenz_game_loader_object" type="application/vnd.turbulenz" width="100%" height="100%">');
                document.write('<p>You need the Turbulenz Engine for this.');
                document.write('<\/p>');
                document.write('<\/object>');
            }"""

        if options.mode == 'plugin-debug':
            tz_engine_div += """
            // If IE
            if (navigator.appName === "Microsoft Internet Explorer")
            {
                window.alert("Sorry, but this sample does not run in development mode in Internet Explorer.");
            }
            var TurbulenzEngine = {
                VMath: null
            };"""

        tz_engine_div += """
        </script>"""

        tz_engine_2d_div = tz_engine_div

    #
    # tz_include_js
    #

    if options.mode in [ 'plugin-debug', 'canvas-debug' ]:
        inc_lines = [ '<script type="text/javascript" src="%s"></script>' % js \
                          for js in inc_js ]
        tz_include_js = "\n".join(inc_lines)
    elif options.mode == 'canvas':
        tz_include_js = '\n<script type="text/javascript" src="%s"></script>' \
            % codefile_rel
    else:
        tz_include_js = "\n"

    #
    # tz_startup_code
    #

    tz_startup_find_best_version_fn = """

            function findBestVersion(request, availableVersions)
            {
                var reqNumbers = request.split(".");
                var candidate;

                for (var vIdx = 0; vIdx < availableVersions.length; vIdx += 1)
                {
                    var ver = availableVersions[vIdx];
                    var verNumbers = ver.split(".");

                    // Check the version has the correct major and minor

                    if ((verNumbers[0] !== reqNumbers[0]) ||
                        (verNumbers[1] !== reqNumbers[1]))
                    {
                        continue;
                    }

                    // If there is already a candidate, compare point and build

                    if (candidate)
                    {
                        if (verNumbers[2] > candidate[2])
                        {
                            candidate = verNumbers;
                            continue;
                        }
                        if ((verNumbers[2] === candidate[2]) &&
                            (verNumbers[3] > candidate[3]))
                        {
                            candidate = verNumbers;
                            continue;
                        }
                    }
                    else
                    {
                        candidate = verNumbers;
                    }
                }

                if (candidate)
                {
                    candidate = candidate.join(".");
                }
                return candidate;
            }"""

    tz_startup_plugin_unload_code = """

            // Engine unload
            var previousOnBeforeUnload = window.onbeforeunload;
            window.onbeforeunload = function ()
            {
                try {
                    loader.unloadEngine();
                } catch (e) {
                }
                if (previousOnBeforeUnload) {
                    previousOnBeforeUnload.call(this);
                }
            };"""

    tz_startup_plugin_check_and_load_code = tz_startup_find_best_version_fn + """

            var now = Date.now || function () { return new Date().valueOf(); };
            var loadDeadline = now() + 5 * 1000;  // 5 seconds
            var loadInterval = 500;               // 0.5 seconds

            var attemptLoad = function attemptLoadFn()
            {
                // Check plugin and load engine
                var err = 0;
                if (!loader) {
                    err = "no loader DOM element";
                }
                if (err === 0 &&
                    !loader.loadEngine &&
                    loader.hasOwnProperty &&
                    !loader.hasOwnProperty('loadEngine')) {
                    err = "loader has no 'loadEngine' property";
                }
                if (err === 0 &&
                    !loader.getAvailableEngines &&
                    !loader.hasOwnProperty('getAvailableEngines')) {
                    err = "no 'getAvailableEngines'. Plugin may be "
                            + "an older version.";
                }

                if (err === 0)
                {
                    var availableEngines = loader.getAvailableEngines();
                    var samplesVersion = '""" + engine_version_2 + """';
                    var requestVersion =
                        findBestVersion(samplesVersion, availableEngines);
                    if (!requestVersion)
                    {
                        err = "No engines installed that are compatible with "
                                + "version " + samplesVersion;
                    }
                    else
                    {
                        config.version = requestVersion;
                    }
                }

                if (err === 0)
                {
                    // Plugin is in place
                    if (!loader.loadEngine(config))
                    {
                        window.alert("Call to loadEngine failed");
                    }
                    return;
                }

                // Continue to wait for the plugin
                if (loadDeadline >= now()) {
                    window.setTimeout(attemptLoad, loadInterval);
                } else {
                    window.alert("No Turbulenz Loader found ("+err+")");
                }
            };
            attemptLoad();"""

    if options.mode == 'plugin-debug':
        tz_startup_code = "\n" + rendered_js.lstrip('\n') + """

        // Engine startup
        window.onload = function ()
        {
            var loader =
                document.getElementById('turbulenz_game_loader_object');
            var appEntry = TurbulenzEngine.onload;
            var appShutdown = TurbulenzEngine.onunload;
            var appMathDevice = TurbulenzEngine.VMath;
            if (!appEntry)
            {
                window.alert("TurbulenzEngine.onload has not been set");
                return;
            }
            var progressCB = function progressCBFn(msg)
            {
                if ('number' !== typeof msg) {
                    window.alert("Error during engine load: " + msg);
                    return;
                }
                // Progress update here
            };
            var config = {
                run: function runFn(engine) {
                    TurbulenzEngine = engine;
                    TurbulenzEngine.onload = appEntry;
                    TurbulenzEngine.onunload = appShutdown;
                    TurbulenzEngine.VMath = appMathDevice;
                    engine.setTimeout(appEntry, 0);
                },
                progress: progressCB
            };""" + tz_startup_plugin_unload_code + """

            """ + tz_startup_plugin_check_and_load_code + """

        };  // window.onload()"""

    elif options.mode == 'plugin':
        tz_startup_code = """

        window.onload = function ()
        {
            var loader = document.getElementById('turbulenz_game_loader_object');
            var config = {
                url: '""" + codefile_rel + """'
            };""" + tz_startup_plugin_unload_code + """

            """ + tz_startup_plugin_check_and_load_code + """

        };  // window.onload()"""

    else:
        tz_startup_code = ""
        if options.hybrid:
            tz_startup_code += """
        var TurbulenzEnginePlugin = null;"""
        if options.mode == 'canvas-debug':
            tz_startup_code += "\n" + rendered_js.lstrip('\n') + "\n"

        tz_startup_code += """
        // Engine startup
        window.onload = function ()
        {
            var appEntry = TurbulenzEngine.onload;
            var appShutdown = TurbulenzEngine.onunload;
            if (!appEntry) {
                window.alert("TurbulenzEngine.onload has not been set");
                return;
            }

            var canvas =
                document.getElementById('turbulenz_game_engine_canvas');"""

        if options.hybrid:
            tz_startup_code += """
            var loader =
                document.getElementById('turbulenz_game_loader_object');"""

        tz_startup_code += """

            var startCanvas = function startCanvasFn()
            {
                if (canvas.getContext && canvasSupported)
                {
                    TurbulenzEngine = WebGLTurbulenzEngine.create({
                        canvas: canvas,
                        fillParent: true
                    });

                    if (!TurbulenzEngine) {
                        window.alert("Failed to init TurbulenzEngine (canvas)");
                        return;
                    }

                    TurbulenzEngine.onload = appEntry;
                    TurbulenzEngine.onunload = appShutdown;
                    appEntry()
                }
            }"""

        # Unloading code

        tz_startup_code += """

            var previousOnBeforeUnload = window.onbeforeunload;
            window.onbeforeunload = function ()
            {
                if (TurbulenzEngine.onunload) {
                    TurbulenzEngine.onunload.call(this);
                }"""
        if options.hybrid:
            tz_startup_code += """
                if (loader.unloadEngine) {
                    loader.unloadEngine();
                }
                if (previousOnBeforeUnload) {
                    previousOnBeforeUnload.call(this);
                }"""
        tz_startup_code += """
            };  // window.beforeunload"""


        # In hybrid mode, nothing can start until the engine is
        # loaded so wrap the canvas startup code in loader calls,
        # otherwise just call it immediately.

        if options.hybrid:
            tz_startup_code += """
            var config = {
                run: function (engine)
                {
                    TurbulenzEnginePlugin = engine;
                    startCanvas();
                },
            };

            if (!loader || !loader.loadEngine || !loader.loadEngine(config))
            {
                window.alert("Failed to load Turbulenz Engine.");
                return;
            }"""

        else:
            tz_startup_code += """

            startCanvas();"""

        tz_startup_code += """
        };  // window.onload()
"""

    context['tz_engine_div'] = tz_engine_div
    context['tz_engine_2d_div'] = tz_engine_2d_div
    context['tz_include_js'] = tz_include_js
    context['tz_startup_code'] = tz_startup_code
    context['tz_sdk_version'] = engine_version
