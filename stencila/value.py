"""
Type and packaing and unpacking of data values
"""

# pylint: disable=redefined-builtin,too-many-return-statements,too-many-branches,no-member

import base64
import json
from io import BytesIO
from collections import OrderedDict

import inspect
import glob
import re
import sphinxcontrib.napoleon
import sphinxcontrib.napoleon.docstring
import matplotlib
import numpy
import pandas
import six


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
        return 'number'
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
        raise RuntimeError('Unhandled Python type: ' + type_)


def pack(value):
    """
    Pack an object into a value package

    :param value: A Python value
    :returns: A value package
    """
    type_ = type(value)
    format_ = 'json'

    if value is None:
        data = None
    elif type_ == 'boolean':
        data = value
    elif type_ in ('integer', 'number'):
        data = value
    elif type_ == 'string':
        data = value
    elif type_ in ('array', 'object'):
        data = value
    elif type_ == 'function':
        return pack_function(value)
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
                column_type = 'number'
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
            columns[column] = values
        data = OrderedDict([('type', 'table'), ('data', columns)])
    elif type_ == 'matplotlib':
        image = BytesIO()
        matplotlib.pyplot.savefig(image, format='png')
        type_ = 'image'
        src = 'data:image/png;base64,' + base64.encodestring(image.getvalue()).decode()
        return {'type': type_, 'src': src}
    else:
        raise RuntimeError('Unable to pack object\n  type: ' + type_)

    return {'type': type_, 'format': format_, 'data': data}


def pack_function(func=None, file=None, dir=None):
    """
    Pack a function object

    Parses the source of the function (either a string or a file
    path) to extract it's ``description``, ``param``, ``return`` etc
    properties.


    Parameters
    ----------
        func : dict or string
            A ``func`` operation. If a string is supplied then an operation
            object is created with the ``source`` property set to
            the string.

    Returns
    -------
        func : dict
            The compiled ``func`` operation
        messages : list
            A list of messages (e.g errors)
    """
    messages = []

    if func is None:
        if file:
            with open(file) as file_obj:
                func = pack_function(file_obj.read())
            return func
        elif dir:
            count = 0
            for file in glob.glob(dir + '/*.py'):
                pack_function(file=file)
                count += 1
            return count
        else:
            raise RuntimeError('No function provided to compile!')
    elif callable(func):
        func_obj = func
        func = {
            'type': 'function'
        }
        func_name = func_obj.__code__.co_name
    elif isinstance(func, str) or isinstance(func, bytes):
        # Parse function source and extract properties from the Function object
        source = func
        scope = {}
        six.exec_(source, scope)

        # Get name of function
        names = [key for key in scope.keys() if not key.startswith('__')]
        if len(names) > 1:
            messages.append({
                'type': 'warning',
                'message': 'More than one function or object defining in function source: %s' % names
            })
        func_name = names[-1]
        func_obj = scope[func_name]

        func = {
            'type': 'function'
        }
    else:
        raise RuntimeError('Unhandled type')

    # Extract parameter specifications
    func_spec = inspect.getargspec(func_obj)
    args = func_spec.args
    if func_spec.varargs:
        args.append(func_spec.varargs)
    if func_spec.keywords:
        args.append(func_spec.keywords)
    params = []
    for index, name in enumerate(args):
        param = {
            'name': name
        }
        if name == func_spec.varargs:
            param['repeat'] = True
        elif name == func_spec.keywords:
            param['extend'] = True
        if func_spec.defaults:
            defaults_index = len(args) - len(func_spec.defaults) + index
            if defaults_index > -1:
                default = func_spec.defaults[defaults_index]
                param['default'] = {
                    'type': type(default),
                    'data': default
                }
        params.append(param)

    # Get docstring and parse it for extra parameter specs
    docstring = func_obj.__doc__
    docstring_params = {}
    docstring_returns = {}
    if docstring:
        docstring = trim_docstring(docstring)
        config = sphinxcontrib.napoleon.Config(napoleon_use_param=True, napoleon_use_rtype=True)
        docstring = sphinxcontrib.napoleon.docstring.NumpyDocstring(docstring, config, what='function').lines()
        docstring = sphinxcontrib.napoleon.docstring.GoogleDocstring(docstring, config, what='function').lines()

        summary = docstring[0]
        description = ''
        pattern = re.compile(r'^:(param|returns|type|rtype)(\s+(\w+))?:(.*)$')
        for line in docstring[1:]:
            match = pattern.match(line)
            if match:
                type_ = match.group(1)
                name = match.group(3)
                desc = match.group(4).strip()
                if type_ == 'param':
                    param = docstring_params.get(name, {})
                    param['description'] = desc
                    docstring_params[name] = param
                elif type_ == 'type':
                    param = docstring_params.get(name, {})
                    param['type'] = desc
                    docstring_params[name] = param
                elif type_ == 'returns':
                    docstring_returns['description'] = desc
                elif type_ == 'rtype':
                    docstring_returns['type'] = desc
            else:
                description += line + '\n'
        description = description.strip()

        if len(summary):
            func.update({'summary': summary})

        if len(description):
            func.update({'description': description})

        for name, spec in docstring_params.items():
            for index, param in enumerate(params):
                if param['name'] == name:
                    params[index].update(spec)
                    break

        if len(docstring_returns):
            func.update({'returns': docstring_returns})

    # Create methods dict
    # FIXME: should use signature not func_name
    methods = {}
    methods[func_name] = {
        'params': params
    }

    func = {
        'name': func_name,
        'methods': methods
    }

    return {
        'type': 'function',
        'format': 'json',
        'data': func
    }


def trim_docstring(docstring):
    """From https://www.python.org/dev/peps/pep-0257/"""
    if not docstring:
        return ''
    # Convert tabs to spaces (following the normal Python rules)
    # and split into a list of lines:
    lines = docstring.expandtabs().splitlines()
    # Determine minimum indentation (first line doesn't count):
    indent = sys.maxsize
    for line in lines[1:]:
        stripped = line.lstrip()
        if stripped:
            indent = min(indent, len(line) - len(stripped))
    # Remove indentation (first line is special):
    trimmed = [lines[0].strip()]
    if indent < sys.maxsize:
        for line in lines[1:]:
            trimmed.append(line[indent:].rstrip())
    # Strip off trailing and leading blank lines:
    while trimmed and not trimmed[-1]:
        trimmed.pop()
    while trimmed and not trimmed[0]:
        trimmed.pop(0)
    # Return a single string:
    return '\n'.join(trimmed)


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

    if not ('type' in pkg and 'data' in pkg):
        raise RuntimeError('Package should have fields `type`, `data`')

    type_ = pkg['type']
    format = pkg.get('format', 'json')
    data = pkg['data']

    if type_ == 'null':
        return None
    elif type_ == 'boolean':
        return data == 'true'
    elif type_ == 'integer':
        return int(data)
    elif type_ == 'number':
        return float(data)
    elif type_ == 'string':
        return data
    elif type_ == 'object' or type_ == 'array':
        return json.loads(data)
    elif type_ == 'table':
        if format == 'json':
            dataframe = pandas.DataFrame()
            for name, column in data['data'].items():
                dataframe[name] = column
            return dataframe
        elif format in ('csv', 'tsv'):
            sep = ',' if format == 'csv' else '\t'
            return pandas.read_csv(BytesIO(data.encode()), sep=sep)
        else:
            raise RuntimeError('Unable to unpack\n  type: ' + type_ + '\n  format: ' + format)
    else:
        raise RuntimeError('Unable to unpack\n  type: ' + type_ + '\n  format: ' + format)
