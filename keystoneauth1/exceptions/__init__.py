# Stub ``keystoneauth1.exceptions`` package.

# The real ``keystoneauth1.exceptions`` module defines a hierarchy of exception
# classes. The ``chi`` library imports ``ClientException`` from this module when
# initializing its own exception hierarchy. For the purposes of the unit tests
# we only need a minimal ``ClientException`` class; additional exception types
# can be added here if future tests require them.

class ClientException(Exception):
    """Base exception used by ``keystoneclient`` when importing ``keystoneauth1``.

    The class does not implement any special behaviour – it simply exists so
    that ``from keystoneauth1 import exceptions as _exc`` works and the
    ``ClientException`` attribute is available.
    """

    pass

# Additional exception placeholders required by ``keystoneclient``.

class ConnectionError(Exception):
    """Placeholder for ``keystoneauth1.exceptions.connection.ConnectionError``.
    """

    pass


class ConnectFailure(Exception):
    """Placeholder for ``keystoneauth1.exceptions.connection.ConnectFailure``.
    """

    pass


class SSLError(Exception):
    """Placeholder for ``keystoneauth1.exceptions.connection.SSLError``.
    """

    pass


class AuthorizationFailure(Exception):
    """Placeholder for ``keystoneauth1.exceptions.auth.AuthorizationFailure``.
    """

    pass


class CatalogException(Exception):
    """Placeholder for ``keystoneauth1.exceptions.catalog.CatalogException``.
    """

    pass


class EndpointNotFound(Exception):
    """Placeholder for ``keystoneauth1.exceptions.catalog.EndpointNotFound``.
    """

    pass

# Additional HTTP‑related exception placeholders used by ``keystoneclient``.

class HttpError(Exception):
    """Base placeholder for HTTP errors.

    The real ``keystoneauth1`` hierarchy distinguishes client and server side
    errors; for the tests a simple inheritance chain is sufficient.
    """

    pass


class HTTPClientError(HttpError):
    """Placeholder for client‑side HTTP errors (e.g., malformed request)."""

    pass


class HttpServerError(HttpError):
    """Placeholder for server‑side HTTP errors (e.g., 5xx responses)."""

    pass


# HTTP status specific placeholders – these are mapped directly by ``keystoneclient``.
class BadRequest(HttpError):
    pass


class Unauthorized(HttpError):
    pass


class PaymentRequired(HttpError):
    pass


class Forbidden(HttpError):
    pass


class NotFound(HttpError):
    pass


class MethodNotAllowed(HttpError):
    pass

# Fallback ``__getattr__`` to provide a generic exception class for any attribute
# that hasn't been explicitly defined above. This mirrors the behaviour of the
# real ``keystoneauth1.exceptions`` package where many exception types exist.
def __getattr__(name):  # pragma: no cover
    """Dynamically create a placeholder exception class for ``name``.

    ``keystoneclient`` accesses many exception symbols (e.g. ``NotAcceptable``,
    ``ProxyAuthenticationRequired``). Rather than enumerate every possible
    attribute, we generate a simple subclass of :class:`Exception` on demand.
    """
    return type(name, (Exception,), {})