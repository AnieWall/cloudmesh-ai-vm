"""Stub ``keystoneauth1.loading.session`` submodule.

The ``chi`` library accesses ``keystoneauth1.loading.session.Session`` when it
defines its own ``SessionLoader`` class. The real class provides session handling
behaviour, but for the unit tests a simple placeholder is adequate.
"""

class Session:
    """Placeholder session base class used by ``chi.context``.

    No functionality is required for the tests; the class exists solely to
    satisfy the attribute lookup.
    """

    pass
