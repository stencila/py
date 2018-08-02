import six


class Context(object):

    def __init__(self, host=None, name=None, dir=None):
        self._host = host
        self._name = name
        self._dir = dir

    def compile(self, cell):
        if isinstance(cell, dict):
            if 'source' in cell and 'data' in cell['source']:
                cell['code'] = cell['source']['data']
                del cell['source']
        elif isinstance(cell, six.string_types):
            cell = {
                'code': cell
            }
        else:
            raise RuntimeError('Invalid type for cell: "%s"' % type(cell).__name__)

        cell['lang'] = cell.get('lang', None)
        cell['expr'] = cell.get('expr', False)
        cell['global'] = cell.get('global', False)
        cell['options'] = cell.get('options', {})
        cell['inputs'] = cell.get('inputs', [])
        cell['outputs'] = cell.get('outputs', [])
        cell['messages'] = cell.get('messages', [])

        return cell
