"""
Used internally to store the instance of the Instance.
Necessary due to circular dependencies and  the fact that
components created in ``Instance.__init__`` need the instance
in their own ``__init__``s
"""

instance = None
