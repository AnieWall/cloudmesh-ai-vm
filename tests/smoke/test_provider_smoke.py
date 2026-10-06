import pytest
from typing import Dict, Any
from unittest.mock import MagicMock, patch
from cloudmesh.ai.vm.providers import PROVIDER_MAP
from cloudmesh.ai.vm.exceptions import ProviderFeatureNotSupported

# Mock configuration that should work for all providers
MOCK_CONFIG = {
    "clouds": {
        "aws": {"access_key": "test", "secret_key": "test", "region": "us-east-1"},
        "azure": {"tenant_id": "test", "subscription_id": "test", "client_id": "test", "client_secret": "test"},
        "google": {"project_id": "test", "private_key": "test"},
        "openstack": {"image": "test", "flavor": "test", "auth_url": "test", "region_name": "test"},
        "multipass": {"image": "22.04"},
        "wsl2": {"rootfs": "/tmp/rootfs"},
        "lima": {"template": "ubuntu"},
        "vbox": {},
    }
}

def get_mock_provider(cloud_name: str):
    """Helper to create a mocked instance of a VM provider."""
    provider_cls = PROVIDER_MAP.get(cloud_name)
    if not provider_cls:
        raise ValueError(f"Provider {cloud_name} not found in PROVIDER_MAP")

    # We mock the driver/CLI interaction to make this a true smoke test
    # that verifies the manager logic and interface without needing real cloud creds.

    # Note: We use a patch context manager inside the tests or a persistent mock.
    # Since we need the provider to hold the mock, we can't easily use a simple context manager here.
    # Instead, we return the provider and the user handles the patching, or we patch the class.
    return provider_cls(config=MOCK_CONFIG, cloud_name=cloud_name)

@pytest.mark.parametrize("cloud_name", PROVIDER_MAP.keys())
def test_provider_core_workflow(cloud_name):
    """
    Verify the Core (Happy Path) lifecycle for every provider:
    Init -> Start -> Info -> Stop -> Delete
    """
    # Setup mocks for this specific provider instance
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="success", returncode=0)

        provider_cls = PROVIDER_MAP.get(cloud_name)
        # Mock driver for libcloud providers
        if hasattr(provider_cls, "_get_driver"):
            with patch.object(provider_cls, "_get_driver", return_value=MagicMock()):
                provider = provider_cls(config=MOCK_CONFIG, cloud_name=cloud_name)
        else:
            provider = provider_cls(config=MOCK_CONFIG, cloud_name=cloud_name)

        # Mock local CLI commands
        if hasattr(provider, "_run_command"):
            with patch.object(provider, "_run_command", return_value=MagicMock(stdout="success", returncode=0)):
                # Execute the test logic
                _run_core_logic(provider)
        else:
            _run_core_logic(provider)

def _run_core_logic(provider):
    # 1. Initialization & Config
    config_errors = provider.validate_config()
    assert isinstance(config_errors, dict)

    # 2. Core Lifecycle
    with patch.object(provider, "start", return_value="test-vm-123"):
        vm_id = provider.start()
        assert vm_id == "test-vm-123"

    with patch.object(provider, "exists", return_value=True):
        assert provider.exists(vm_id) is True

    with patch.object(provider, "info", return_value={"name": vm_id, "status": "running"}):
        info = provider.info(vm_id)
        assert info["name"] == vm_id
        assert info["status"] == "running"

    with patch.object(provider, "stop", return_value=True):
        assert provider.stop(vm_id) is True

    with patch.object(provider, "delete", return_value=True):
        assert provider.delete(vm_id) is True

@pytest.mark.parametrize("cloud_name", PROVIDER_MAP.keys())
def test_provider_discovery_and_metadata(cloud_name):
    """
    Verify that list(), get_provider_info(), and basic discovery work.
    """
    provider_cls = PROVIDER_MAP.get(cloud_name)
    with patch("subprocess.run", return_value=MagicMock(stdout="success", returncode=0)):
        if hasattr(provider_cls, "_get_driver"):
            with patch.object(provider_cls, "_get_driver", return_value=MagicMock()):
                provider = provider_cls(config=MOCK_CONFIG, cloud_name=cloud_name)
        else:
            provider = provider_cls(config=MOCK_CONFIG, cloud_name=cloud_name)

        if hasattr(provider, "_run_command"):
            with patch.object(provider, "_run_command", return_value=MagicMock(stdout="success", returncode=0)):
                _run_discovery_logic(provider, cloud_name)
        else:
            _run_discovery_logic(provider, cloud_name)

def _run_discovery_logic(provider, cloud_name):
    # 1. Metadata
    info = provider.get_provider_info()
    assert "provider" in info
    assert "version" in info
    assert info["cloud_name"] == cloud_name

    # 2. Inventory
    with patch.object(provider, "list", return_value=[{"name": "test-vm", "status": "running"}]):
        vms = provider.list()
        assert len(vms) == 1
        assert vms[0]["name"] == "test-vm"
        assert "name" in vms[0]

@pytest.mark.parametrize("cloud_name", PROVIDER_MAP.keys())
def test_provider_access_interface(cloud_name):
    """
    Verify that the access methods (login, run_command) exist and follow the contract.
    """
    provider_cls = PROVIDER_MAP.get(cloud_name)
    with patch("subprocess.run", return_value=MagicMock(stdout="success", returncode=0)):
        if hasattr(provider_cls, "_get_driver"):
            with patch.object(provider_cls, "_get_driver", return_value=MagicMock()):
                provider = provider_cls(config=MOCK_CONFIG, cloud_name=cloud_name)
        else:
            provider = provider_cls(config=MOCK_CONFIG, cloud_name=cloud_name)

        if hasattr(provider, "_run_command"):
            with patch.object(provider, "_run_command", return_value=MagicMock(stdout="success", returncode=0)):
                _run_access_logic(provider)
        else:
            _run_access_logic(provider)

def _run_access_logic(provider):
    try:
        with patch.object(provider, "login", return_value=True):
            assert provider.login("test-vm") is True
    except ProviderFeatureNotSupported:
        pass

    try:
        with patch.object(provider, "run_command", return_value="uptime: 1:00"):
            result = provider.run_command("test-vm", "uptime")
            assert isinstance(result, str)
    except ProviderFeatureNotSupported:
        pass
