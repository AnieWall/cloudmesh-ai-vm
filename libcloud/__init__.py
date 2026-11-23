"""Stub package for ``libcloud`` to satisfy optional imports in the test suite.

The real ``apache-libcloud`` library is not a mandatory dependency for the core
functionality exercised by the unit tests.  Providing a minimal stub that offers
the symbols required by the provider modules (e.g., ``get_driver`` and the
``Provider`` enum) allows the code to import without pulling in the external
dependency.
"""

# The subpackages are created as separate modules.
# No additional initialization required.