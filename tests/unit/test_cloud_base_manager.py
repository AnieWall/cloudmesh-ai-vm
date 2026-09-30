import pytest

from cloudmesh.ai.vm.CloudBaseManager import CloudBaseManager
from cloudmesh.ai.vm.exceptions import ProviderFeatureNotSupported


@pytest.fixture
def provider():
    return CloudBaseManager(config={})


def test_get_security_groups_not_supported(provider):
    with pytest.raises(ProviderFeatureNotSupported):
        provider.get_security_groups()


def test_upload_key_not_supported(provider):
    with pytest.raises(ProviderFeatureNotSupported):
        provider.upload_key("test.pub", "test-key")


def test_delete_key_not_supported(provider):
    with pytest.raises(ProviderFeatureNotSupported):
        provider.delete_key("test-key")


def test_add_security_group_rule_not_supported(provider):
    with pytest.raises(ProviderFeatureNotSupported):
        provider.add_security_group_rule(
            "test-sg", "tcp", "22", "0.0.0.0/0", "ingress"
        )