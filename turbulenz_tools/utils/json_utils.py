# Copyright (c) 2009-2013 Turbulenz Limited
"""
Utilities to manipulate JSON data.
"""

import logging
LOG = logging.getLogger('asset')

def merge_dictionaries(outof, into, prefix='\t'):
    """Merge the dictionary 'outof' into the dictionary 'into'. If matching keys are found and the value is a
    dictionary, then the sub dictionary is merged."""
    for k in outof.keys():
        if k in into:
            if isinstance(outof[k], dict):
                LOG.debug("%sMerging:%s", prefix, k)
                into[k] = merge_dictionaries(outof[k], into[k], prefix + '\t')
            else:
                LOG.debug("%sSkipping:%s", prefix, k)
        else:
            into[k] = outof[k]
    return into

def float_to_string(f):
    """Unitiliy float encoding which clamps floats close to 0 and 1 and uses %g instead of repr()."""
    if abs(f) < 1e-6:
        return "0"
    elif abs(1 - f) < 1e-6:
        return "1"
    return "%g" % (f)

def metrics(asset):
    """Generate a collection of simple size metrics about the asset."""
    def __approximate_size(num):
        """Convert a file size to human-readable form."""
        for x in [' bytes', 'KB', 'MB', 'GB', 'TB']:
            if num < 1024.0:
                return "%3.1f%s" % (num, x)
            num /= 1024.0

    def __count_nodes(nodes):
        """Recursively count the nodes."""
        num_nodes = len(nodes)
        for n in nodes.itervalues():
            if 'nodes' in n:
                num_nodes += __count_nodes(n['nodes'])
        return num_nodes

    m = { }
    for k in asset.keys():
        if isinstance(asset[k], dict):
            m['num_' + k] = len(asset[k])
        elif isinstance(asset[k], list):
            m['num_' + k] = len(asset[k])
    if 'nodes' in asset:
        m['num_nodes_recurse'] = __count_nodes(asset['nodes'])
    if 'num_geometries' in m and m['num_geometries']:
        m['total_primitives'] = 0
        m['total_positions'] = 0
        m['approximate_size'] = 0
        for _, shape in asset['geometries'].items():
            if 'surfaces' in shape:
                for _, surface in shape['surfaces'].items():
                    m['total_primitives'] += int(surface['numPrimitives'])
            else:
                if 'numPrimitives' in shape:
                    m['total_primitives'] += int(shape['numPrimitives'])
            if 'POSITION' in shape['inputs']:
                position_source = shape['inputs']['POSITION']['source']
                if position_source in shape['sources']:
                    positions = shape['sources'][position_source]
                    m['total_positions'] += len(positions['data']) / positions['stride']
            for _, source in shape['sources'].items():
                m['approximate_size'] += len(source['data']) * 4      # Assume float per vertex element attribute
            if 'triangles' in shape:
                m['approximate_size'] += len(shape['triangles']) * 2  # Assume short per index
            elif 'quads' in shape:
                m['approximate_size'] += len(shape['quads']) * 2      # Assume short per index
        m['average_primitives'] = m['total_primitives'] / m['num_geometries']
        m['average_positions'] = m['total_positions'] / m['num_geometries']
        m['approximate_readable_size'] = __approximate_size(m['approximate_size'])
    return m

def log_metrics(asset):
    """Output the metrics to the log."""
    m = metrics(asset)
    keys = m.keys()
    keys.sort()
    for k in keys:
        LOG.info('%s:%s', k, m[k])
