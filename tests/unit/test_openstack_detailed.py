from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from cloudmesh.ai.vm.openstack.OpenstackManager import OpenstackManager

MOCK_CONFIG = {
    "clouds": {
        "test-openstack": {
            "image": "test-image",
            "flavor": "test-flavor",
            "auth_url": "https://example.invalid/v3/",
            "region_name": "RegionOne",
            "floating_ip_pool": "public",
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
        return OpenstackManager(
            MOCK_CONFIG,
            cloud_name="test-openstack",
        )

    def test_list_sdk_success(self, provider):
        conn = MagicMock()

        server = SimpleNamespace(
            name="vm1",
            id="id1",
            status="ACTIVE",
            addresses={
                "private": [{"addr": "10.0.0.1"}],
                "floating": [{"addr": "1.2.3.4"}],
            },
            image=SimpleNamespace(name="img1"),
            flavor=SimpleNamespace(name="flv1"),
        )

        conn.compute.servers.return_value = [server]

        with patch.object(provider, "_get_sdk_conn", return_value=conn):
            vms = provider.list()

        assert len(vms) == 1
        assert vms[0]["name"] == "vm1"
        assert vms[0]["id"] == "id1"
        assert vms[0]["status"] == "ACTIVE"
        assert vms[0]["ip"] == "1.2.3.4"
        assert vms[0]["image"] == "img1"
        assert vms[0]["flavor"] == "flv1"

    @pytest.mark.parametrize(
        ("addresses", "expected_ip"),
        [
            # Real openstacksdk format on Jetstream: one network, the floating
            # IP is marked by OS-EXT-IPS:type.
            (
                {
                    "auto_allocated_network": [
                        {"addr": "10.0.140.67", "OS-EXT-IPS:type": "fixed"},
                        {"addr": "149.165.169.251", "OS-EXT-IPS:type": "floating"},
                    ]
                },
                "149.165.169.251",
            ),
            # No floating IP attached.
            (
                {"auto_allocated_network": [{"addr": "10.0.140.67", "OS-EXT-IPS:type": "fixed"}]},
                "No IP",
            ),
            # No addresses at all.
            (None, "No IP"),
        ],
    )
    def test_list_sdk_floating_ip_by_type(self, provider, addresses, expected_ip):
        """list() finds the floating IP by its OS-EXT-IPS:type, not by network name."""
        conn = MagicMock()
        server = SimpleNamespace(
            name="vm1",
            id="id1",
            status="ACTIVE",
            addresses=addresses,
            image=SimpleNamespace(name="img1"),
            flavor=SimpleNamespace(name="flv1"),
        )
        conn.compute.servers.return_value = [server]

        with patch.object(provider, "_get_sdk_conn", return_value=conn):
            vms = provider.list()

        assert vms[0]["ip"] == expected_ip

    def test_get_floating_ip_success(self, provider):
        """Verify _get_floating_ip correctly parses the 'addresses' output."""
        mock_output = "network: a=10.0.0.1,net-id=net1; floating: a=1.2.3.4,net-id=net2"
        with (
            patch.object(provider, "_run_cli_command", return_value=mock_output),
            patch.object(provider, "_find_node", return_value=MagicMock(public_ips=[])),
        ):
            ip = provider._get_floating_ip("test-vm")
            assert ip == "1.2.3.4"

    def test_get_floating_ip_none(self, provider):
        """Verify _get_floating_ip returns None when no floating IP is assigned."""
        mock_output = "network: a=10.0.0.1,net-id=net1"
        with (
            patch.object(provider, "_run_cli_command", return_value=mock_output),
            patch.object(provider, "_find_node", return_value=MagicMock(public_ips=[])),
        ):
            ip = provider._get_floating_ip("test-vm")
            assert ip is None

    def test_assign_floating_ip_success(self, provider):
        mock_fip = MagicMock(id="fip-123", ip="1.2.3.4")
        mock_node = MagicMock(id="node-123")
        
        # We need to mock the driver since we are testing the Manager's orchestration
        provider.driver = MagicMock()
        provider.driver.ex_create_floating_ip.return_value = mock_fip
        provider.driver._find_node.return_value = mock_node

        with (
            patch.object(provider, "_find_node", return_value=mock_node),
            patch.object(provider, "wait_for_active", return_value=True),
            patch.object(provider, "_wait_for_network", return_value=True),
        ):
            ip = provider.assign_floating_ip("test-vm")
            assert ip == "1.2.3.4"
            provider.driver.ex_attach_floating_ip_to_node.assert_called_once_with(
                mock_node, mock_fip
            )

    def test_release_floating_ip_success(self, provider):
        mock_fip = MagicMock(id="fip-123")
        mock_node = MagicMock(id="node-123")
        
        provider.driver = MagicMock()
        
        with patch.object(provider, "_find_node", return_value=mock_node):
            result = provider.release_floating_ip("test-vm")
            assert result is True
            provider.driver.ex_detach_floating_ip_from_node.assert_called_once_with(
                mock_node, mock_fip
            )
            provider.driver.ex_delete_floating_ip.assert_called_once_with(mock_fip)
