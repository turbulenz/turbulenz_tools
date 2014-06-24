# Copyright (c) 2010-2014 Turbulenz Limited
"""
Utility functions for finding and outputing dependencies
"""

from os.path import join, exists, abspath
from jinja2 import meta

__version__ = '1.0.0'

def find_file_in_dirs(filename, dirs, error_on_multiple = False):
    found = []
    for d in dirs:
        fn = join(d, filename)
        if exists(fn):
            if error_on_multiple:
                if fn not in found:
                    found.append(fn)
            else:
                return abspath(fn)
    if error_on_multiple:
        if len(found) > 1:
            raise Exception("File '%s' matched several locations: %s" % found)
        if len(found) == 1:
            return abspath(found[0])
    return None

# pylint: disable=W0102
def find_dependencies(input_file, templatedirs, env, exceptions=[]):
    """
    Find jinja2 dependency list.  Files listed in 'exceptions' do not
    generate exceptions if not found.
    """

    total_set = set()

    def find_dependencies_recurse(file_path):
        new_deps = []

        # Parse the file and extract the list of references

        with open(file_path, "r") as f:
            ast = env.parse(f.read().decode('utf-8'))

            # For each reference, find the absolute path.  If no file
            # is found and the reference was not listed in exceptions,
            # throw an error.

            for reference in meta.find_referenced_templates(ast):
                reference_path = find_file_in_dirs(reference, templatedirs)
                if reference_path is None:
                    if reference in exceptions:
                        continue
                    raise Exception("cannot find file '%s' referenced in "
                                    "'%s'" % (reference, file_path))
                new_deps.append(reference_path)

        for dep in new_deps:
            # Make sure we don't have a circular reference
            if dep not in total_set:
                total_set.add(dep)
                find_dependencies_recurse(dep)
        return

    top_file = find_file_in_dirs(input_file, templatedirs)
    if top_file is None:
        raise Exception("cannot find file '%s'" % input_file)
    total_set.add(top_file)
    find_dependencies_recurse(top_file)

    sorted_total = []
    for x in total_set:
        sorted_total.append(x)

    sorted_total.sort()
    return sorted_total
# pylint: enable=W0102
