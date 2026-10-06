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

        # 2. Mock CLI output (Tab separated as per our new implementation)
        mock_cli_output = "vm1\tid1\tACTIVE\timg1\tflv1\tnet1"
        with patch.object(provider, "_run_cli_command", return_value=mock_cli_output) as mock_run:
            vms = provider.list()

            assert len(vms) == 1
            assert vms[0]["name"] == "vm1"
            assert vms[0]["id"] == "id1"
            assert vms[0]["status"] == "ACTIVE"

            # Verify the new optimized command is used
            mock_run.assert_called_once_with([
                "openstack", "server", "list", "--format", "value",
                "-c", "Name", "-c", "ID", "-c", "Status", "-c", "Image", "-c", "Flavor", "-c", "Networks"
            ])


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
        with patch.object(provider, "_run_cli_command") as mock_run:
            # 1. list free IPs, 2. add IP to server, 3. get floating IP result
            # The 3rd response must match the expected OpenStack value format
            mock_run.side_effect = [
                "ip-123",
                "Success",
                "network: a=10.0.0.1; floating: a=1.2.3.4,net-id=net2"
            ]
            ip = provider.assign_floating_ip("test-vm")
            assert ip == "1.2.3.4"
            assert mock_run.call_count == 3

    def test_release_floating_ip_success(self, provider):
        """Test releasing a floating IP via CLI."""
        with patch.object(provider, "_run_cli_command") as mock_run:
            # 1. find floating IP, 2. remove from server, 3. delete the IP
            mock_run.side_effect = ["network: a=10.0.0.1; floating: a=1.2.3.4,net-id=net2", "Success", "Success"]

            result = provider.release_floating_ip("test-vm")
            assert result is True
            assert mock_run.call_count == 3

    def test_get_security_group_info_success(self, provider):
        """Verify optimized get_security_group_info parsing."""
        mock_output = "sg-123\tsg-name\tThis is a description"
        with patch.object(provider, "_run_cli_command", return_value=mock_output) as mock_run:
            info = provider.get_security_group_info("sg-name")
            assert info == {"id": "sg-123", "name": "sg-name", "description": "This is a description"}
            mock_run.assert_called_once_with([
                "openstack", "security", "group", "show", "sg-name",
                "-f", "value", "-c", "id", "-c", "name", "-c", "description"
            ])

    def test_list_security_group_rules_success(self, provider):
        """Verify optimized list_security_group_rules parsing."""
        mock_output = "rule-1\ttcp\t80\t80\t0.0.0.0/0\nrule-2\tudp\t53\t53\t10.0.0.0/8"
        with patch.object(provider, "_run_cli_command", return_value=mock_output) as mock_run:
            rules = provider.list_security_group_rules("sg-name")
            assert len(rules) == 2
            assert rules[0]["id"] == "rule-1"
            assert rules[0]["protocol"] == "tcp"
            assert rules[0]["remote_ip"] == "0.0.0.0/0"
            assert rules[1]["id"] == "rule-2"

            mock_run.assert_called_once_with([
                "openstack", "security", "group", "rule", "list", "sg-name",
                "-f", "value", "-c", "id", "-c", "protocol", "-c", "port_range_min",
                "-c", "port_range_max", "-c", "remote_ip"
            ])

