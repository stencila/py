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
