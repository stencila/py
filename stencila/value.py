import json
from io import BytesIO

import pandas


def type(value):
    """
    Get the type code for a value

    :param value: A Python Value
    :returns: Type code for value
    """
    type_ = __builtins__['type'](value).__name__

    if value is None:
        return 'null'
    elif type_ == 'bool':
        return 'boolean'
    elif type_ == 'int':
        return 'integer'
    elif type_ == 'float':
        return 'float'
    elif type_ == 'str':
        return 'string'
    elif type_ in ('tuple', 'list'):
        return 'array'
    elif type_ == 'dict':
        type_ = value.get('type')
        if type_ and isinstance(type_, str):
            return type_
        else:
            return 'object'
    elif isinstance(value, pandas.DataFrame):
        return 'table'
    else:
        raise RuntimeError('Unable to pack object\n  type: ' + type_)


def pack(value):
    """
    Pack an object into a data package

    :param thing: The Python object
    :returns: A data package
    """
    type_ = type(value)
    format = 'text'

    if value is None:
        content = 'null'
    elif type_ == 'boolean':
        content = 'true' if value else 'false'
    elif type_ in ('integer', 'float'):
        content = repr(value)
    elif type_ == 'string':
        content = value
    elif type_ in ('array', 'object'):
        format = 'json'
        content = json.dumps(value, separators=(',', ':'))
    elif type_ == 'table':
        format = 'csv'
        content = value.to_csv(index=False)
    else:
        raise RuntimeError('Unable to pack object\n  type: ' + type_)

    return {'type': type_, 'format': format, 'content': content}


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

    if not ('type' in pkg and 'format' in pkg and 'content' in pkg):
        raise RuntimeError('Package should have fields `type`, `format`, `content`')

    type_ = pkg['type']
    format = pkg['format']
    content = pkg['content']

    if type_ == 'null':
        return None
    elif type_ == 'boolean':
        return content == 'true'
    elif type_ == 'integer':
        return int(content)
    elif type_ == 'float':
        return float(content)
    elif type_ == 'string':
        return content
    elif type_ == 'object':
        return json.loads(content)
    elif type_ == 'array':
        return json.loads(content)
    elif type_ == 'table':
        if format in ('csv', 'tsv'):
            sep = ',' if format == 'csv' else '\t'
            return pandas.read_csv(BytesIO(content.encode()), sep=sep)
        else:
            raise RuntimeError('Unable to unpack\n  type: ' + type_ + '\n  format: ' + format)
    else:
        raise RuntimeError('Unable to unpack\n  type: ' + type_ + '\n  format: ' + format)
