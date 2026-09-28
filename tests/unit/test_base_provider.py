import pytest

from cloudmesh.ai.vm.base import BaseVMProvider
from cloudmesh.ai.vm.exceptions import ProviderFeatureNotSupported


def test_login_not_supported():
    """Unsupported login should raise the standard provider exception."""
    provider = BaseVMProvider(config={})

    with pytest.raises(
        ProviderFeatureNotSupported,
        match="does not support the feature: login"
    ):
        provider.login("test-vm")