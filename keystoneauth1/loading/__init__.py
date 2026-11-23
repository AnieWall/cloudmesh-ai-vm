"""Stub implementation of the ``keystoneauth1.loading`` package.

Only a very small subset of the real ``keystoneauth1.loading`` API is required
for the ``chi`` library used in the Chameleon manager tests. The real library
provides many configuration and authentication helpers. For the purposes of the
unit tests we implement minimal no‑op functions that return simple placeholder
values. This allows the import ``from keystoneauth1 import loading`` to succeed
without pulling in heavyweight dependencies.
"""

from __future__ import annotations

# The ``chi`` context module expects the following callables. They are used only
# for configuration handling, which is mocked out in the test suite, so we can
# safely provide very small implementations.

def get_session_conf_options():
    """Return an empty list of configuration option objects.

    In the genuine library this would return a list of ``oslo_config`` option
    objects describing session‑related settings. The tests never inspect the
    returned objects, so an empty list is sufficient.
    """
    return []


def get_adapter_conf_options():
    """Return an empty list of adapter configuration option objects.

    The real implementation provides options for request adapters. The test
    environment does not use these, so an empty list works as a stub.
    """
    return []


def load_auth_from_conf_options(conf, group):
    """Return a simple dummy authentication object.

    ``chi`` may replace this function at runtime, but for import time we just
    need an object that can be used as a placeholder. A ``type`` with a ``__repr__``
    is enough.
    """
    class DummyAuth:
        def __repr__(self):
            return "<DummyAuth>"

    return DummyAuth()


def load_adapter_from_conf_options(conf, session):
    """Return the provided ``session`` unchanged.

    The real function would construct an HTTP adapter based on the configuration.
    For tests we simply return the session object that was passed in.
    """
    return session

# Ensure the ``session`` submodule is available as an attribute of the loading
# package. ``chi.context`` expects ``loading.session.Session`` to exist.
from . import session  # noqa: F401  (imported for side‑effect)

# Fallback attribute handler: any undefined attribute accessed on the ``loading``
# package will resolve to a no‑op callable. This mirrors the behaviour of the
# real ``keystoneauth1.loading`` module where many helper functions exist.
def __getattr__(name):  # pragma: no cover
    def _placeholder(*args, **kwargs):
        return None
    return _placeholder

# ``chi.context`` calls ``loading.register_auth_conf_options`` during module
# initialization. The real function registers configuration options with the
# oslo_config ``cfg.CONF`` object. Our stub registers the minimal option stubs
# defined in ``keystoneauth1.loading.conf``.
def register_auth_conf_options(conf, group):  # pragma: no cover
    """Register minimal auth configuration options and common auth groups.

    ``chi.context`` expects the ``auth_section`` and ``auth_type`` options to be
    present in the ``chi`` configuration group. It also later attempts to set
    overrides in plugin‑specific groups such as ``chi.auth.v3token``. To avoid
    ``NoSuchGroupError`` we pre‑register a few typical auth groups.
    """
    from .conf import _AUTH_SECTION_OPT, _AUTH_TYPE_OPT
    # Register the core options in the provided group.
    try:
        conf.register_opt(_AUTH_SECTION_OPT, group=group)
        conf.register_opt(_AUTH_TYPE_OPT, group=group)
    except Exception:
        pass
    # Pre‑create common auth plugin groups to prevent missing‑group errors.
    try:
        from oslo_config import cfg as oslo_cfg

        for plugin in ("v3token", "v3password", "v2password", "v2token"):
            auth_group_name = f"{group}.auth.{plugin}"
            conf.register_group(oslo_cfg.OptGroup(auth_group_name))
            # Register the same auth options inside the plugin‑specific group.
            conf.register_opt(_AUTH_SECTION_OPT, group=auth_group_name)
            conf.register_opt(_AUTH_TYPE_OPT, group=auth_group_name)
    except Exception:
        # Silently ignore if the group already exists or registration fails.
        pass

# ``loading.register_adapter_conf_options`` is also referenced, but the tests
# do not rely on any specific behaviour. Provide a harmless placeholder.
def register_adapter_conf_options(conf, group):  # pragma: no cover
    return None

# Provide a minimal ``get_available_plugin_loaders`` implementation used by the
# ``chi`` context during initialization. Returning an empty dict ensures the
# subsequent iteration yields no plugins, which is acceptable for the unit
# tests that mock out all chi functionality.
def get_available_plugin_loaders():  # pragma: no cover
    return {}
