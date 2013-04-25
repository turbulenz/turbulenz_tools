# This code is based on an xml2json.py script found at:
# https://gist.github.com/raw/434945/2a0615b2bd07ece2248a968609284b3ba0d5e466/xml2json.py
#
# It has been modified to fit our package style and asset types.
# Also supports stripping out namespaces and converting values to native types.
#
# All modifications are:
# Copyright (c) 2010-2011,2013 Turbulenz Limited

from simplejson import loads as json_loads, dumps as json_dumps, encoder as json_encoder

# pylint: disable=W0404
try:
    from xml.etree import cElementTree as ElementTree
except ImportError:
    from xml.etree import ElementTree
# pylint: enable=W0404

from turbulenz_tools.tools.json2json import float_to_string

__version__ = '1.0.0'
__dependencies__ = ['turbulenz_tools.tools.json2json']

#######################################################################################################################

def to_native(a):
    """Parse the string into native types."""
    if a is None:
        return None

    try:
        int_number = int(a)
    except ValueError:
        pass
    else:
        return int_number

    try:
        float_number = float(a)
    except ValueError:
        pass
    else:
        return float_number

    parts = a.split()

    try:
        int_list = [int(x) for x in parts]
    except ValueError:
        pass
    else:
        return int_list

    try:
        float_list = [float(x) for x in parts]
    except ValueError:
        pass
    else:
        return float_list

    return a

def elem2internal(elem, strip=True, convert_types=False):
    """Convert an Element into an internal dictionary (not JSON!)."""
    if convert_types:
        _prepare = to_native
    else:
        _prepare = lambda a: a

    def _elem2internal(elem):
        d = { }
        for key, value in elem.attrib.items():
            d['@'+key] = _prepare(value)

        # loop over subelements to merge them
        for subelem in elem:
            v = _elem2internal(subelem)
            tag = subelem.tag
            value = v[tag]
            try:
                # add to existing list for this tag
                d[tag].append(value)
            except AttributeError:
                # turn existing entry into a list
                d[tag] = [d[tag], value]
            except KeyError:
                # add a new non-list entry
                d[tag] = value
        text = elem.text
        tail = elem.tail
        if strip:
            # ignore leading and trailing whitespace
            if text:
                text = text.strip()
            if tail:
                tail = tail.strip()
        text = _prepare(text)
        tail = _prepare(tail)

        if tail:
            d['#tail'] = tail

        if d:
            # use #text element if other attributes exist
            if text:
                d["#text"] = text
        else:
            # text is the value if no attributes

            # The following line used to read:
            #  >> d = text or None
            # But we now convert '0' to 0 and this resulted in None instead of 0.
            # So it has been updated to:
            d = text
        return { elem.tag: d }

    return _elem2internal(elem)

def internal2elem(pfsh, factory=ElementTree.Element):
    """Convert an internal dictionary (not JSON!) into an Element."""
    attribs = { }
    text = None
    tail = None
    sublist = [ ]
    tag = pfsh.keys()
    if len(tag) != 1:
        raise ValueError("Illegal structure with multiple tags: %s" % tag)
    tag = tag[0]
    value = pfsh[tag]
    if isinstance(value, dict):
        for k, v in value.items():
            if k[:1] == "@":
                attribs[k[1:]] = v
            elif k == "#text":
                text = v
            elif k == "#tail":
                tail = v
            elif isinstance(v, list):
                for v2 in v:
                    sublist.append(internal2elem({k:v2}, factory=factory))
            else:
                sublist.append(internal2elem({k:v}, factory=factory))
    else:
        text = value
    e = factory(tag, attribs)
    for sub in sublist:
        e.append(sub)
    e.text = text
    e.tail = tail
    return e

def elem2json(elem, strip=True, indent=0, convert_types=False):
    """Convert an ElementTree or Element into a JSON string."""
    if hasattr(elem, 'getroot'):
        elem = elem.getroot()

    internal = elem2internal(elem, strip=strip, convert_types=convert_types)

    # Module 'simplejson' has no 'encoder' member
    # pylint: disable=E1101
    json_encoder.FLOAT_REPR = float_to_string
    # pylint: enable=E1101
    if indent > 0:
        output = json_dumps(internal, sort_keys=True, indent=indent)
    else:
        output = json_dumps(internal, sort_keys=True, separators=(',', ':'))

    return output

def json2elem(json_string, factory=ElementTree.Element):
    """Convert a JSON string into an Element."""
    return internal2elem(json_loads(json_string), factory)

def xml2json(xml_string, strip=True, indent=0, convert_types=False):
    """Convert an XML string into a JSON string."""
    elem = ElementTree.fromstring(xml_string)
    return elem2json(elem, strip=strip, indent=indent, convert_types=convert_types)

def json2xml(json_string, factory=ElementTree.Element):
    """Convert a JSON string into an XML string."""
    elem = internal2elem(json_loads(json_string), factory)
    return ElementTree.tostring(elem)
