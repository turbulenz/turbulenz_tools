# Copyright (c) 2012-2013 Turbulenz Limited

from jinja2 import Environment, FileSystemLoader, ChoiceLoader
from jinja2 import TemplateNotFound, TemplateSyntaxError, BaseLoader
from logging import getLogger

from turbulenz_tools.tools.toolsexception import ToolsException

import os
import re

LOG = getLogger(__name__)
LF_RE = re.compile(r".?\r.?", re.DOTALL)

############################################################

class DefaultTemplateLoader(BaseLoader):
    """
    Class that loads a named template from memory
    """

    def __init__(self, name, template):
        BaseLoader.__init__(self)
        self.name = name
        self.template = template

    def get_source(self, env, template):
        if template == self.name:
            LOG.info("Request for template '%s'.  Using default registered", template)
            return self.template, None, lambda: True
        raise TemplateNotFound(template)

class UTF8FileSystemLoader(FileSystemLoader):
    """
    Class that loads a template from a given path, removing any utf8
    BOMs.
    """

    def __init__(self, searchpath):
        FileSystemLoader.__init__(self, searchpath)
        self._path = searchpath

    def get_source(self, env, name):
        fn = os.path.join(self._path, name)
        if not os.path.exists(fn):
            raise TemplateNotFound(name)

        d = read_file_utf8(fn)
        return d, None, lambda: True

############################################################

def _sanitize_crlf(m):
    v = m.group(0)
    if 3 == len(v):
        if '\n' == v[0]:
            return '\n' + v[2]
        if '\n' == v[2]:
            return v[0] + '\n'
    elif 2 == len(v):
        if '\n' in v:
            return '\n'
    return v.replace('\r', '\n')

# Read a file, handling any utf8 BOM
def read_file_utf8(filename):
    with open(filename, 'rb') as f:
        text = f.read().decode('utf-8-sig')

        # This is unpleasant, but it is thorough.  This is the
        # single-pass equivalent of:
        # return (in_data.replace('\r\n', '\n').replace('\n\r', '\n'))\
        #     .replace('\r', '\n');
        return LF_RE.sub(_sanitize_crlf, text)

############################################################

def env_create(options, default_template=None):
    """
    Setup a jinja env based on the tool options
    """

    LOG.info("Template dirs:")
    for t in options.templatedirs:
        LOG.info(" - '%s'", t)

    loaders = [ UTF8FileSystemLoader(t) for t in options.templatedirs ]
    if default_template is not None:
        loaders.append(DefaultTemplateLoader('default', default_template))

    _loader = ChoiceLoader(loaders)
    env = Environment(loader = _loader,
                      block_start_string = '/*{%',
                      block_end_string = '%}*/',
                      variable_start_string = '/*{{',
                      variable_end_string = '}}*/',
                      comment_start_string = '/*{#',
                      comment_end_string = '#}*/')
    return env

############################################################

def env_load_template(env, in_file):
    """
    Load a single template into the environment, handling the
    appropriate errors.  Returns the loaded template
    """

    try:
        return env.get_template(in_file)
    except TemplateNotFound as e:
        raise ToolsException('template not found: %s' % str(e))
    except TemplateSyntaxError as e:
        raise ToolsException('template syntax error: %s' % str(e))

############################################################

def env_load_templates(env, inputs):
    """
    Load an array of templates into the environment.  Returns the
    loaded templates as a list
    """

    return [env_load_template(env, i) for i in inputs]
