import base64
import json
from io import BytesIO
from collections import OrderedDict

import matplotlib
import numpy
import pandas


class Context(object):

    def __init__(self, host=None, name=None, dir=None):
        self._host = host
        self._name = name
        self._dir = dir

    @staticmethod
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
        elif callable(value):
            return 'function'
        else:
            raise RuntimeError('Unable to pack object\n  type: ' + type_)

    @staticmethod
    def pack(value):
        """
        Pack an object into a value package

        :param value: A Python value
        :returns: A value package
        """
        type_ = Context.type(value)
        format_ = 'text'

        if value is None:
            data = 'null'
        elif type_ == 'boolean':
            data = 'true' if value else 'false'
        elif type_ in ('integer', 'float'):
            data = repr(value)
        elif type_ == 'string':
            data = value
        elif type_ in ('array', 'object'):
            format_ = 'json'
            data = json.dumps(value, separators=(',', ':'))
        elif type_ == 'table':
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
                elif col.dtype == numpy.object and values:
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
            data = OrderedDict([('type', 'table'), ('data', columns)])
        elif type_ == 'matplotlib':
            image = BytesIO()
            matplotlib.pyplot.savefig(image, format='png')
            type_ = 'image'
            src = 'data:image/png;base64,' + base64.encodestring(image.getvalue()).decode()
            return {'type': type_, 'src': src}
        else:
            raise RuntimeError('Unable to pack object\n  type: ' + type_)

        return {'type': type_, 'data': data}
