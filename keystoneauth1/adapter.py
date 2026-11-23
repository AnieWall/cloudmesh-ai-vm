"""Stub ``keystoneauth1.adapter`` module.

The ``keystoneclient`` library imports this module to obtain the ``Adapter``
class used for HTTP communication. The unit tests mock out any network
interactions, so a minimal placeholder is sufficient.
"""

class Adapter:  # pragma: no cover
    """Placeholder adapter class.

    The real implementation provides request handling; for the test suite we
    never instantiate or use it directly.
    """

    pass

# Provide a minimal ``LegacyJsonAdapter`` subclass to satisfy ``keystoneclient``.
class LegacyJsonAdapter(Adapter):  # pragma: no cover
    """Placeholder subclass used by ``keystoneclient.httpclient``.
    """

    pass
