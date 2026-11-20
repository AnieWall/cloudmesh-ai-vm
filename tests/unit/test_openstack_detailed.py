from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from cloudmesh.ai.vm.openstack.OpenstackManager import OpenstackManager
from tests.utils.ip_synthetic import synthetic_ip_pair

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

    # ---------------------------------------------------------------------
    # Helper: deterministic random IP pair (synthetic)
    # ---------------------------------------------------------------------
    def _random_ips(self, count: int = 2):  # pragma: no cover – used only in tests
        """Return ``count`` distinct IPv4 addresses.

        Internally we delegate to :func:`synthetic_ip_pair` which produces
        private‑range addresses safe for unit‑testing.  The helper mirrors the
        signature that existed before the PR so the existing test logic can be
        reused unchanged.
        """
        if count != 2:
            raise ValueError("Synthetic helper currently only supports a pair")
        fixed, floating = synthetic_ip_pair(mode="private")
        return [fixed, floating]

    def test_list_sdk_success(self, provider):
        conn = MagicMock()

        # Generate a pair of synthetic IPs instead of hard‑coding values.
        fixed, fip = self._random_ips(2)

        server = SimpleNamespace(
            name="vm1",
            id="id1",
            status="ACTIVE",
            addresses={
                "private": [{"addr": fixed}],
                "floating": [{"addr": fip}],
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
        assert vms[0]["ip"] == fip
        assert vms[0]["image"] == "img1"
        assert vms[0]["flavor"] == "flv1"

    # ---------------------------------------------------------------------
    # Various address layouts – each yields a distinct floating‑IP extraction
    # path.  ``LIST_ADDRESS_LAYOUTS`` maps a layout name to a callable that
    # receives ``fixed`` and ``floating`` IP strings and returns a tuple:
    # (addresses_dict, expected_floating_ip).
    # ---------------------------------------------------------------------
    LIST_ADDRESS_LAYOUTS = {
        "floating_after_fixed": lambda fixed, fip: (
            {"auto_allocated_network": [{"addr": fixed, "OS-EXT-IPS:type": "fixed"},
                                          {"addr": fip, "OS-EXT-IPS:type": "floating"}]},
            fip,
        ),
        "floating_before_fixed": lambda fixed, fip: (
            {"auto_allocated_network": [{"addr": fip, "OS-EXT-IPS:type": "floating"},
                                          {"addr": fixed, "OS-EXT-IPS:type": "fixed"}]},
            fip,
        ),
        "floating_on_second_network": lambda fixed, fip: (
            {"private": [{"addr": fixed, "OS-EXT-IPS:type": "fixed"}],
             "public": [{"addr": fip, "OS-EXT-IPS:type": "floating"}]},
            fip,
        ),
        "network_named_floating": lambda fixed, fip: (
            {"private": [{"addr": fixed}], "floating": [{"addr": fip}]},
            fip,
        ),
        "fixed_only": lambda fixed, fip: (
            {"auto_allocated_network": [{"addr": fixed, "OS-EXT-IPS:type": "fixed"}]},
            "No IP",
        ),
        "no_addresses": lambda fixed, fip: (None, "No IP"),
    }

    @pytest.mark.parametrize("layout", sorted(LIST_ADDRESS_LAYOUTS))
    def test_list_sdk_floating_ip_by_type(self, provider, layout):
        """list() extracts the floating IP for every supported address layout."""
        fixed, fip = self._random_ips(2)
        addresses, expected_ip = self.LIST_ADDRESS_LAYOUTS[layout](fixed, fip)

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

    def test_list_sdk_floating_ip_per_server(self, provider):
        """Each server receives its own floating IP – no sharing across VMs."""
        servers = []
        expected = {}
        # Create five distinct VMs each with its own synthetic IP pair.
        for idx in range(5):
            fixed, fip = self._random_ips(2)
            vm = SimpleNamespace(
                name=f"vm{idx}",
                id=f"id{idx}",
                status="ACTIVE",
                addresses={"net": [{"addr": fixed, "OS-EXT-IPS:type": "fixed"},
                                 {"addr": fip, "OS-EXT-IPS:type": "floating"}]},
                image=SimpleNamespace(name="img1"),
                flavor=SimpleNamespace(name="flv1"),
            )
            servers.append(vm)
            expected[f"id{idx}"] = fip

        conn = MagicMock()
        conn.compute.servers.return_value = servers

        with patch.object(provider, "_get_sdk_conn", return_value=conn):
            vms = provider.list()

        # Validate that the mapping of VM id → reported floating IP matches expectations.
        assert {vm["id"]: vm["ip"] for vm in vms} == expected

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
