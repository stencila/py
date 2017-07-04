import base64
import json
from io import BytesIO
from collections import OrderedDict

import matplotlib
import numpy
import pandas


def type(value):
    """
    Get the type code for a value

    :param value: A Python value
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
    elif (
            isinstance(value, (matplotlib.figure.Figure, matplotlib.artist.Artist)) or
            (type_ == 'list' and len(value) == 1 and isinstance(value[0], matplotlib.artist.Artist))
    ):
        # Use the special 'matplotlib' type to identify plot values that need
        # to be converted to the standard 'image' type during `pack()`
        return 'matplotlib'
    elif type_ in ('tuple', 'list'):
        return 'array'
    elif type_ == 'dict':
        type_ = value.get('type')
        if type_ and isinstance(type_, str):
            return type_
        return 'object'
    elif isinstance(value, pandas.DataFrame):
        return 'table'
    else:
        raise RuntimeError('Unable to pack object\n  type: ' + type_)


def pack(value):
    """
    Pack an object into a value package

    :param value: A Python value
    :returns: A value package
    """
    type_ = type(value)
    format_ = 'text'

    if value is None:
        content = 'null'
    elif type_ == 'boolean':
        content = 'true' if value else 'false'
    elif type_ in ('integer', 'float'):
        content = repr(value)
    elif type_ == 'string':
        content = value
    elif type_ in ('array', 'object'):
        format_ = 'json'
        content = json.dumps(value, separators=(',', ':'))
    elif type_ == 'table':
        format_ = 'json'
        columns = OrderedDict()
        for column in value.columns:
            col = value[column]
            # See the list of numpy data types at
            # https://docs.scipy.org/doc/numpy/reference/arrays.scalars.html#arrays-scalars-built-in
            values = list(col)
            if col.dtype in (numpy.bool_, numpy.bool8):
                column_type = 'boolean'
                values = [bool(row) for row in values]
            elif col.dtype in (numpy.int8, numpy.int16, numpy.int32, numpy.int64):
                column_type = 'integer'
                values = [int(row) for row in values]
            elif col.dtype in (numpy.float16, numpy.float32, numpy.float64):
                column_type = 'float'
                values = [float(row) for row in values]
            elif col.dtype in (numpy.str_, numpy.unicode_,):
                column_type = 'string'
            elif col.dtype == numpy.object and len(values) > 0:
                # Get the type from the type of the first value
                column_type = {
                    str: 'string'
                }.get(__builtins__['type'](values[0]))
            else:
                column_type = col.dtype.name
            columns[column] = OrderedDict([
                ('type', column_type),
                ('values', values)
            ])
        content = json.dumps(OrderedDict([('type', 'table'), ('data', columns)]))
    elif type_ == 'matplotlib':
        image = BytesIO()
        matplotlib.pyplot.savefig(image, format='png')
        type_ = 'image'
        format_ = 'src'
        content = 'data:image/png;base64,' + base64.encodestring(image.getvalue()).decode()
    else:
        raise RuntimeError('Unable to pack object\n  type: ' + type_)

    return {'type': type_, 'format': format_, 'content': content}


def unpack(pkg):
    """
    Unpack a value package into a Python value

    :param pkg: The value package
    :returns: A Python value
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
    elif type_ == 'object' or type_ == 'array':
        return json.loads(content)
    elif type_ == 'table':
        if format == 'json':
            table = json.loads(content, object_pairs_hook=OrderedDict)
            df = pandas.DataFrame()
            for name, column in table['data'].items():
                df[name] = column['values']
            return df
        elif format in ('csv', 'tsv'):
            sep = ',' if format == 'csv' else '\t'
            return pandas.read_csv(BytesIO(content.encode()), sep=sep)
        else:
            raise RuntimeError('Unable to unpack\n  type: ' + type_ + '\n  format: ' + format)
    else:
        raise RuntimeError('Unable to unpack\n  type: ' + type_ + '\n  format: ' + format)
