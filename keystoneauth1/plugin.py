"""Stub ``keystoneauth1.plugin`` module.

The real ``keystoneauth1`` library provides a ``plugin`` submodule with various
authentication plugin implementations. The ``keystoneclient`` library imports
this module solely for its existence; the unit tests mock out any functionality
that would use it. Providing an empty module satisfies the import without
introducing heavy dependencies.
"""

# Define a minimal constant expected by ``keystoneclient``.
AUTH_INTERFACE = "auth_interface"

# No additional symbols are required for the test suite.
