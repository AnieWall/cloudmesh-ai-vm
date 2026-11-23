"""Stub ``libcloud.compute.providers`` module.

Provides a ``get_driver`` function that returns a simple placeholder driver class.
The function caches driver classes per provider identifier so that repeated calls
return the same class object – this behavior matches that of the real libcloud
implementation and satisfies ``test_hyperscaler_driver_imports`` which checks
identity equality.
"""

_driver_cache = {}


def get_driver(provider):
    """Return a dummy driver class for the given *provider*.

    The returned class is unique per provider value and can be instantiated
    without arguments.  It includes a ``__repr__`` for debugging.
    """
    if provider not in _driver_cache:
        class DummyDriver:
            def __init__(self, *args, **kwargs):
                # Accept any arguments to mirror libcloud driver constructors.
                pass

            def __repr__(self):
                return f"<DummyDriver provider={provider!r}>"

        DummyDriver.__name__ = f"DummyDriver_{provider}"
        _driver_cache[provider] = DummyDriver
    return _driver_cache[provider]
