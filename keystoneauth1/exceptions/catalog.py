"""Stub ``keystoneauth1.exceptions.catalog`` module.

Provides the ``EndpointNotFound`` exception class used by ``ChameleonManager``.
"""


class EndpointNotFound(Exception):
    """Exception raised when an endpoint cannot be found in the service catalog.

    The real ``keystoneauth1`` library defines additional attributes, but for the
    purposes of the test suite a simple subclass of ``Exception`` is sufficient.
    """
