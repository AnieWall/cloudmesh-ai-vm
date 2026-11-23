"""Stub configuration constants for ``keystoneauth1.loading``.

The ``chi`` library imports ``_AUTH_SECTION_OPT`` and ``_AUTH_TYPE_OPT`` from
``keystoneauth1.loading.conf``. The real values are ``oslo_config`` option
objects, but the tests only need them to exist, not to provide full functionality.
"""

# Provide lightweight option stubs that expose a ``dest`` attribute, matching the
# interface expected by ``chi.context``. The real ``keystoneauth1`` library uses
# ``oslo_config.cfg.StrOpt`` objects; for our purposes we only need the ``dest``
# attribute.

class _OptionStub:
    def __init__(self, dest: str):
        self.dest = dest
        # ``oslo_config`` checks for ``multi`` to determine if an option accepts
        # multiple values. For our stub we default to ``False``.
        self.multi = False
        # The ``type`` attribute is used by ``oslo_config`` to convert values;
        # we default to ``str`` which is sufficient for the test suite.
        self.type = str

_AUTH_SECTION_OPT = _OptionStub("auth_section")
_AUTH_TYPE_OPT = _OptionStub("auth_type")
