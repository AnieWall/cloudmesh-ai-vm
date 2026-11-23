"""Package marker for ``keystoneauth1.identity``.

The real ``keystoneauth1`` library provides several identity plugins. The test
suite only requires the ``v3`` submodule with the ``OidcAccessToken`` class, so
this ``__init__`` file can remain empty.
"""
