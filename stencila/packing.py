import json
from io import BytesIO

import pandas

def pack(thing):
    """
    Pack an object into a data package

    :param thing: The Python object
    :returns: A data package
    """
    typ = type(thing).__name__
    format = 'text'
    value = thing

    if thing is None:
        typ = 'null'
        value = 'null'
    elif typ == 'bool':
        value = 'true' if thing else 'false'
    elif typ in ('int', 'float'):
        if typ == 'float':
            typ = 'flt'
        value = repr(thing)
    elif typ == 'str':
        pass
    elif typ in ('tuple', 'list', 'dict'):
        typ = 'obj' if typ == 'dict' else 'arr'
        format = 'json'
        value = json.dumps(thing, separators=(',', ':'))
    elif isinstance(thing, pandas.DataFrame):
        typ = 'tab'
        format = 'csv'
        value = thing.to_csv(index=False)
    else:
        raise RuntimeError('Unable to pack object\n  type: ' + typ)

    return {'type': typ, 'format': format, 'value': value}


def unpack(pkg):
    """
    Unpack a data package into an object

    :param pkg: The data package
    :returns: A Python object
    """
    if isinstance(pkg, str):
        pkg = json.loads(pkg)

    if not isinstance(pkg, dict):
        raise RuntimeError('Package should be an `Object`')

    if not ('type' in pkg and 'format' in pkg and 'value' in pkg):
        raise RuntimeError('Package should have fields `type`, `format`, `value`')

    typ = pkg['type']
    format = pkg['format']
    value = pkg['value']

    if typ == 'null':
        return None
    elif typ == 'bool':
        return value == 'true'
    elif typ == 'int':
        return int(value)
    elif typ == 'flt':
        return float(value)
    elif typ == 'str':
        return value
    elif typ == 'obj':
        return json.loads(value)
    elif typ == 'arr':
        return json.loads(value)
    elif typ == 'tab':
        if format in ('csv', 'tsv'):
            sep = ',' if format == 'csv' else '\t'
            return pandas.read_csv(BytesIO(value.encode()), sep=sep)
        else:
            raise RuntimeError('Unable to unpack\n  type: ' + typ + '\n  format: ' + format)
    else:
        raise RuntimeError('Unable to unpack\n  type: ' + typ + '\n  format: ' + format)
