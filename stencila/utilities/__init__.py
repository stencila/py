import collections


def update(d, u):
    for k, v in u.items():
        if isinstance(v, collections.Mapping):
            default = v.copy()
            default.clear()
            r = update(d.get(k, default), v)
            d[k] = r
        else:
            d[k] = v
    return d


def path_to_format(path):
    root, ext = os.path.splitext(path)
    if len(ext) > 1:
        return ext[1:]
    return None
