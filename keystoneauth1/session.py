"""Stub implementation of ``keystoneauth1.session``.

Only the ``Session`` base class and ``SessionLoader`` are required for the
``chi`` context module. The real library implements a sophisticated HTTP session
with token handling; for testing we provide lightweight placeholders.
"""

from __future__ import annotations

from unittest.mock import MagicMock


class Session:
    """Minimal base class for ``keystoneauth1.session.Session``.

    The ``chi`` context defines a custom subclass ``_SessionWithAccessTokenRefresh``
    that inherits from ``session.Session``. No specific functionality is needed
    for the unit tests, so an empty class is sufficient.
    """

    pass


class SessionLoader:
    """Simple loader that returns a mock session object.

    The real ``SessionLoader`` reads configuration and constructs a concrete
    ``Session`` instance. In the test environment the resulting session is never
    used for network calls, so returning a ``MagicMock`` keeps the API compatible
    without side effects.
    """

    def load_from_conf_options(self, *args, **kwargs):  # pragma: no cover
        """Return a ``MagicMock`` representing a session.

        ``*args`` and ``**kwargs`` are accepted for signature compatibility.
        """
        return MagicMock()
