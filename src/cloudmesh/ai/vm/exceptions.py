class CloudMeshError(Exception):
    """Base exception for all cloudmesh-ai-vm errors."""


class VMProviderError(CloudMeshError):
    """Exception raised for general provider-related failures."""
    # NOTE: ``VMProviderError`` is used throughout the code base to propagate
    # errors from provider implementations.  To guarantee that no credential‑
    # like information ever leaks via exception messages, we automatically
    # sanitise the supplied error text using the shared ``sanitize_output``
    # helper.  The helper removes patterns such as bearer tokens, API keys,
    # passwords, secrets, and generic tokens.
    #
    # By centralising the sanitisation here, we avoid the need to modify every
    # individual ``raise VMProviderError(...)`` site (which would be error‑
    # prone and would require numerous repetitive patches).  All subclasses –
    # ``VMAuthError``, ``VMResourceError``, ``VMNetworkError`` – inherit this
    # behaviour automatically.
    def __init__(self, message: str):
        from cloudmesh.ai.command._shared.providers_utils import sanitize_output

        # Ensure we always work with a string representation.
        safe_message = sanitize_output(str(message))
        super().__init__(safe_message)
class VMAuthError(VMProviderError):
    """Exception raised when authentication with the cloud provider fails."""


class VMResourceError(VMProviderError):
    """Exception raised when a requested cloud resource (image, flavor, VM) is not found."""


class VMNetworkError(VMProviderError):
    """Exception raised for network-related failures, such as SSH timeouts or IP resolution issues."""


class ConfigError(CloudMeshError):
    """Exception raised for configuration-related issues."""


class ProviderFeatureNotSupported(VMProviderError):
    """Exception raised when a provider does not support a specific feature."""

    def __init__(self, provider_name: str, feature: str):
        self.provider_name = provider_name
        self.feature = feature
        self.message = (
            f"Provider '{provider_name}' does not support the feature: {feature}"
        )
        super().__init__(self.message)
