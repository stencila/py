"""
Used internally to store the instance of Host.
Necessary due to circular dependencies and  the fact that
components created in ``Host.__init__`` need the instance
in their own ``__init__``s
"""

host = None
