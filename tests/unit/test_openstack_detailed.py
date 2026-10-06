import pytest
from unittest.mock import MagicMock, patch
from cloudmesh.ai.vm.openstack.OpenstackManager import OpenstackManager
from cloudmesh.ai.vm.exceptions import VMProviderError, VMResourceError

# Mock configuration for OpenStack tests
MOCK_CONFIG = {
    "clouds": {
        "test-openstack": {
            "image": "test-image",
            "flavor": "test-flavor",
            "auth_url": "https://example.invalid/v3/",
            "region_name": "RegionOne",
        }
    }
}

class TestOpenstackDetailed:
    """
    Detailed unit tests for OpenstackManager focused on CLI fallbacks,
    floating IP logic, and error handling.
    """

    @pytest.fixture
    def provider(self):
        driver = MagicMock()
        with patch.object(OpenstackManager, "_get_driver", return_value=driver):
            provider = OpenstackManager(MOCK_CONFIG, cloud_name="test-openstack")
            provider.driver = driver
            return provider

    def test_run_cli_command_success(self, provider):
        """Verify that _run_cli_command correctly sets env vars and returns output."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="success-output")

            result = provider._run_cli_command(["openstack", "server", "list"])

            assert result == "success-output"
            # Verify env vars were set
            args, kwargs = mock_run.call_args
            assert kwargs["env"]["OS_CLOUD"] == "test-openstack"

    def test_run_cli_command_failure(self, provider):
        """Verify that _run_cli_command raises VMProviderError on non-zero exit."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stderr="some error")

            with pytest.raises(VMProviderError, match="CLI command failed"):
                provider._run_cli_command(["openstack", "server", "list"])

    def test_list_cli_fallback_success(self, provider):
        """Test that list() falls back to CLI when libcloud returns no results."""
        # 1. Mock libcloud to return empty list
        provider.driver.list_nodes.return_value = []

        # 2. Mock CLI output
        mock_cli_output = "Name\tID\tStatus\tImage\tFlavor\tNetworks\nvm1\tid1\tACTIVE\timg1\tflv1\tnet1"
        with patch.object(provider, "_run_cli_command", return_value=mock_cli_output):
            vms = provider.list()

            assert len(vms) == 1
            assert vms[0]["name"] == "vm1"
            assert vms[0]["id"] == "id1"
            assert vms[0]["status"] == "ACTIVE"

    def test_get_floating_ip_success(self, provider):
        """Verify _get_floating_ip correctly parses the 'addresses' output."""
        mock_output = "network: a=10.0.0.1,net-id=net1; floating: a=1.2.3.4,net-id=net2"
        with patch.object(provider, "_run_cli_command", return_value=mock_output):
            ip = provider._get_floating_ip("test-vm")
            assert ip == "1.2.3.4"

    def test_get_floating_ip_none(self, provider):
        """Verify _get_floating_ip returns None when no floating IP is assigned."""
        mock_output = "network: a=10.0.0.1,net-id=net1"
        with patch.object(provider, "_run_cli_command", return_value=mock_output):
            ip = provider._get_floating_ip("test-vm")
            assert ip is None

    def test_assign_floating_ip_success(self, provider):
        """Test assigning a floating IP via CLI."""
        # Mock list of free IPs
        provider._run_cli_command = MagicMock(side_effect=[
            MagicMock(stdout="ip-123\n", returncode=0), # list free IPs
            MagicMock(stdout="Success", returncode=0),  # associate IP
            "1.2.3.4"                                   # _get_floating_ip result
        ])
        # Note: because _run_cli_command is a mock, we need to handle the return values
        # But we can just mock the internal calls
        with patch.object(provider, "_run_cli_command") as mock_run:
            mock_run.side_effect = ["ip-123", "Success", "network: a=10.0.0.1; floating: a=1.2.3.4,net-id=net1"]
            ip = provider.assign_floating_ip("test-vm")
            assert ip == "1.2.3.4"
            assert mock_run.call_count == 3

    def test_release_floating_ip_success(self, provider):
        """Test releasing a floating IP via CLI."""
        with patch.object(provider, "_run_cli_command") as mock_run:
            # 1. find floating IP
            mock_run.side_effect = ["network: a=10.0.0.1; floating: a=1.2.3.4,net-id=net2", "Success", "Success"]

            result = provider.release_floating_ip("test-vm")
            assert result is True
            assert mock_run.call_count == 3
