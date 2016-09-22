"""
Used internally to store the instance of the session.
Necessary due to circular dependencies and  the fact that
components created in ``Session.__init__`` need the session instance
in their own ``__init__``s
"""

instance = None
