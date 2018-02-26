"""
Get the version of this package

Based on http://stackoverflow.com/a/17638236/4625911
"""

# pylint: disable=invalid-name

import os.path
from pkg_resources import get_distribution, DistributionNotFound

try:
    dist = get_distribution('stencila')
    dist_loc = os.path.normcase(dist.location)
    here = os.path.normcase(__file__)
    if not here.startswith(os.path.join(dist_loc, 'stencila')):
        raise DistributionNotFound
except DistributionNotFound:
    __version__ = '0.0.0'
else:
    __version__ = dist.version
