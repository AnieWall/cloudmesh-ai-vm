"""Regression tests for Azure public IP lifecycle management (issue #177)."""

from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import MagicMock

from cloudmesh.ai.vm.azure.AzureManager import Provider as AzureProvider


def _configure_public_ip_mocks(provider, public_ip):
    """Configure realistic Azure ARM ownership and association responses."""
    provider.driver.connection.request.return_value = SimpleNamespace(
        object={
            "id": public_ip.id,
            "tags": {
                "cloudmesh-ai-vm:managed": "true",
                "cloudmesh-ai-vm:resource": "public-ip",
            },
        }
    )

    provider.driver.ex_get_public_ip.return_value = SimpleNamespace(
        id=public_ip.id,
        name=public_ip.name,
        extra={
            "ipAddress": public_ip.extra.get("ipAddress"),
            "ipConfiguration": None,
        },
    )


def test_assign_public_ip_updates_existing_vm_nic():
    """Assignment must associate the public IP with the VM's attached NIC."""
    provider = AzureProvider.__new__(AzureProvider)
    provider.cloud_name = "azure"
    provider.driver = MagicMock()

    provider.get_cloud_config = MagicMock(
        return_value={"resource_group": "rg-test", "subnet": "subnet-123"}
    )

    nic_id = (
        "/subscriptions/sub-test/resourceGroups/rg-network/"
        "providers/Microsoft.Network/networkInterfaces/nic-existing"
    )

    node = SimpleNamespace(
        id="vm-123",
        name="test-vm",
        public_ips=[],
        extra={
            "properties": {
                "networkProfile": {
                    "networkInterfaces": [{"id": nic_id}]
                }
            }
        },
    )

    nic = SimpleNamespace(
        id=nic_id,
        name="nic-existing",
        location="eastus",
        extra={
            "ipConfigurations": [
                {
                    "name": "primary",
                    "properties": {
                        "subnet": {"id": "subnet-123"},
                        "privateIPAllocationMethod": "Dynamic",
                    },
                }
            ]
        },
    )

    public_ip = SimpleNamespace(
        id="/subscriptions/sub-test/resourceGroups/rg-test/"
           "providers/Microsoft.Network/publicIPAddresses/pip-test",
        name="pip-test",
        extra={"ipAddress": "203.0.113.10"},
    )

    original_nic_properties = deepcopy(nic.extra)

    provider.get_vm = MagicMock(return_value=node)
    updated_nic = deepcopy(nic)
    updated_nic.extra["ipConfigurations"][0]["properties"][
        "publicIPAddress"
    ] = {"id": public_ip.id}

    provider.driver.ex_get_nic.side_effect = [nic, updated_nic]
    provider.driver.ex_create_public_ip.return_value = public_ip
    _configure_public_ip_mocks(provider, public_ip)

    result = provider.assign_floating_ip("test-vm")

    assert nic.extra == original_nic_properties

    provider.driver.ex_update_nic_properties.assert_called_once()
    provider.driver.ex_create_network_interface.assert_not_called()

    args = provider.driver.ex_update_nic_properties.call_args
    assert args.kwargs["network_interface"] is nic
    assert args.kwargs["resource_group"] == "rg-network"

    properties = args.kwargs["properties"]
    ip_config = properties["ipConfigurations"][0]
    assert ip_config["properties"]["publicIPAddress"]["id"] == public_ip.id
    assert ip_config["properties"]["subnet"]["id"] == "subnet-123"
    assert result == "203.0.113.10"


def test_assign_public_ip_cleans_up_after_nic_update_failure():
    """A failed NIC update must not leave a newly allocated public IP."""
    import pytest

    from cloudmesh.ai.vm.exceptions import VMProviderError

    provider = AzureProvider.__new__(AzureProvider)
    provider.cloud_name = "azure"
    provider.driver = MagicMock()
    provider.get_cloud_config = MagicMock(
        return_value={"resource_group": "rg-test", "subnet": "subnet-123"}
    )

    nic_id = (
        "/subscriptions/sub-test/resourceGroups/rg-test/"
        "providers/Microsoft.Network/networkInterfaces/nic-existing"
    )

    node = SimpleNamespace(
        id="vm-123",
        name="test-vm",
        public_ips=[],
        extra={
            "properties": {
                "networkProfile": {
                    "networkInterfaces": [{"id": nic_id}]
                }
            }
        },
    )

    nic = SimpleNamespace(
        id=nic_id,
        name="nic-existing",
        location="eastus",
        extra={
            "ipConfigurations": [
                {
                    "name": "primary",
                    "properties": {
                        "subnet": {"id": "subnet-123"},
                        "privateIPAllocationMethod": "Dynamic",
                    },
                }
            ]
        },
    )

    public_ip = SimpleNamespace(
        id=(
            "/subscriptions/sub-test/resourceGroups/rg-test/"
            "providers/Microsoft.Network/publicIPAddresses/pip-test"
        ),
        name="pip-test",
        extra={"ipAddress": "203.0.113.10"},
    )

    provider.get_vm = MagicMock(return_value=node)
    provider.driver.ex_get_nic.return_value = nic
    provider.driver.ex_create_public_ip.return_value = public_ip
    _configure_public_ip_mocks(provider, public_ip)
    provider.driver.ex_update_nic_properties.side_effect = RuntimeError(
        "Simulated NIC update failure"
    )
    provider.driver.ex_delete_public_ip.return_value = True

    # Azure confirms that the failed update did not attach the public IP.
    provider.driver.ex_get_nic.return_value = nic
    provider.driver.ex_get_public_ip.return_value = public_ip

    with pytest.raises(VMProviderError, match="Simulated NIC update failure"):
        provider.assign_floating_ip("test-vm")

    provider.driver.ex_update_nic_properties.assert_called_once()
    provider.driver.ex_delete_public_ip.assert_called_once_with(public_ip)
    provider.driver.ex_destroy_nic.assert_not_called()



def test_release_managed_public_ip_detaches_before_deletion():
    """Release must detach a managed IP before deleting its resource."""
    provider = AzureProvider.__new__(AzureProvider)
    provider.cloud_name = "azure"
    provider.driver = MagicMock()
    provider.get_cloud_config = MagicMock(
        return_value={"resource_group": "rg-test"}
    )

    nic_id = (
        "/subscriptions/sub-test/resourceGroups/rg-network/"
        "providers/Microsoft.Network/networkInterfaces/nic-existing"
    )
    public_ip_id = (
        "/subscriptions/sub-test/resourceGroups/rg-test/"
        "providers/Microsoft.Network/publicIPAddresses/pip-test"
    )

    node = SimpleNamespace(
        id="vm-123",
        name="test-vm",
        public_ips=["203.0.113.10"],
        extra={
            "properties": {
                "networkProfile": {
                    "networkInterfaces": [{"id": nic_id}]
                }
            }
        },
    )

    nic = SimpleNamespace(
        id=nic_id,
        name="nic-existing",
        location="eastus",
        extra={
            "ipConfigurations": [
                {
                    "name": "primary",
                    "properties": {
                        "subnet": {"id": "subnet-123"},
                        "privateIPAllocationMethod": "Dynamic",
                        "publicIPAddress": {"id": public_ip_id},
                    },
                }
            ]
        },
    )

    public_ip = SimpleNamespace(
        id=public_ip_id,
        name="pip-test",
        extra={
            "ipAddress": "203.0.113.10",
            "ipConfiguration": {
                "id": f"{nic_id}/ipConfigurations/primary"
            },
        },
    )

    detached_public_ip = SimpleNamespace(
        id=public_ip_id,
        name="pip-test",
        extra={"ipAddress": "203.0.113.10"},
    )

    detached_nic = SimpleNamespace(
        id=nic_id,
        name="nic-existing",
        location="eastus",
        extra={
            "ipConfigurations": [
                {
                    "name": "primary",
                    "properties": {
                        "subnet": {"id": "subnet-123"},
                        "privateIPAllocationMethod": "Dynamic",
                    },
                }
            ]
        },
    )

    original_properties = deepcopy(nic.extra)

    provider.get_vm = MagicMock(return_value=node)
    provider.driver.get_node.return_value = node
    provider.driver.ex_get_nic.side_effect = [nic, detached_nic]
    provider.driver.ex_get_public_ip.side_effect = [
        public_ip,
        detached_public_ip,
        detached_public_ip,
    ]

    provider.driver.connection.request.return_value.object = {
        "id": public_ip_id,
        "tags": {
            "cloudmesh-ai-vm:managed": "true",
            "cloudmesh-ai-vm:resource": "public-ip",
        },
    }

    events = []

    def update_nic(*, network_interface, resource_group, properties):
        assert network_interface is nic
        assert resource_group == "rg-network"
        assert "publicIPAddress" not in (
            properties["ipConfigurations"][0]["properties"]
        )
        assert properties["ipConfigurations"][0]["properties"]["subnet"] == {
            "id": "subnet-123"
        }
        events.append("detach")
        return nic

    def delete_public_ip(*args, **kwargs):
        resource = kwargs.get("public_ip", args[0] if args else None)
        assert resource is detached_public_ip
        assert resource.id == public_ip.id
        events.append("delete")
        return True

    provider.driver.ex_update_nic_properties.side_effect = update_nic
    provider.driver.ex_delete_public_ip.side_effect = delete_public_ip

    result = provider.release_floating_ip("test-vm")

    assert result is True
    assert events == ["detach", "delete"]
    assert nic.extra == original_properties
    provider.driver.ex_create_network_interface.assert_not_called()

def test_release_refuses_unmanaged_public_ip():
    """Never detach or delete an Azure public IP without ownership evidence."""
    import pytest

    from cloudmesh.ai.vm.exceptions import VMProviderError

    provider = AzureProvider.__new__(AzureProvider)
    provider.cloud_name = "azure"
    provider.driver = MagicMock()
    provider.get_cloud_config = MagicMock(
        return_value={"resource_group": "rg-test"}
    )

    nic_id = (
        "/subscriptions/sub-test/resourceGroups/rg-test/"
        "providers/Microsoft.Network/networkInterfaces/nic-existing"
    )
    public_ip_id = (
        "/subscriptions/sub-test/resourceGroups/rg-test/"
        "providers/Microsoft.Network/publicIPAddresses/external-ip"
    )

    node = SimpleNamespace(
        id="vm-123",
        name="test-vm",
        public_ips=["203.0.113.10"],
        extra={
            "properties": {
                "networkProfile": {
                    "networkInterfaces": [{"id": nic_id}]
                }
            }
        },
    )

    nic = SimpleNamespace(
        id=nic_id,
        name="nic-existing",
        location="eastus",
        extra={
            "ipConfigurations": [
                {
                    "name": "primary",
                    "properties": {
                        "subnet": {"id": "subnet-123"},
                        "publicIPAddress": {"id": public_ip_id},
                    },
                }
            ]
        },
    )

    public_ip = SimpleNamespace(
        id=public_ip_id,
        name="external-ip",
        extra={"ipAddress": "203.0.113.10"},
    )

    provider.get_vm = MagicMock(return_value=node)
    provider.driver.get_node.return_value = node
    provider.driver.ex_get_nic.return_value = nic
    provider.driver.ex_get_public_ip.return_value = public_ip

    # Azure reports no Cloudmesh ownership tags.
    provider.driver.connection.request.return_value.object = {
        "id": public_ip_id,
        "tags": {"owner": "external"},
    }

    with pytest.raises(
        VMProviderError,
        match="(?i)managed|ownership|unmanaged",
    ):
        provider.release_floating_ip("test-vm")

    provider.driver.ex_update_nic_properties.assert_not_called()
    provider.driver.ex_delete_public_ip.assert_not_called()


def test_assign_does_not_delete_ip_when_failed_update_attached_it():
    """Never delete an allocated IP if Azure reports it is attached."""
    import pytest

    from cloudmesh.ai.vm.exceptions import VMProviderError

    provider = AzureProvider.__new__(AzureProvider)
    provider.cloud_name = "azure"
    provider.driver = MagicMock()
    provider.get_cloud_config = MagicMock(
        return_value={"resource_group": "rg-test", "subnet": "subnet-123"}
    )

    nic_id = (
        "/subscriptions/sub-test/resourceGroups/rg-test/"
        "providers/Microsoft.Network/networkInterfaces/nic-existing"
    )
    public_ip_id = (
        "/subscriptions/sub-test/resourceGroups/rg-test/"
        "providers/Microsoft.Network/publicIPAddresses/pip-test"
    )

    node = SimpleNamespace(
        id="vm-123",
        name="test-vm",
        public_ips=[],
        extra={
            "properties": {
                "networkProfile": {
                    "networkInterfaces": [{"id": nic_id}]
                }
            }
        },
    )

    original_nic = SimpleNamespace(
        id=nic_id,
        name="nic-existing",
        location="eastus",
        extra={
            "ipConfigurations": [
                {
                    "name": "primary",
                    "properties": {
                        "subnet": {"id": "subnet-123"},
                    },
                }
            ]
        },
    )

    attached_nic = SimpleNamespace(
        id=nic_id,
        name="nic-existing",
        location="eastus",
        extra={
            "ipConfigurations": [
                {
                    "name": "primary",
                    "properties": {
                        "subnet": {"id": "subnet-123"},
                        "publicIPAddress": {"id": public_ip_id},
                    },
                }
            ]
        },
    )

    public_ip = SimpleNamespace(
        id=public_ip_id,
        name="pip-test",
        extra={"ipAddress": "203.0.113.10"},
    )

    provider.get_vm = MagicMock(return_value=node)
    provider.driver.ex_get_nic.side_effect = [
        original_nic,
        attached_nic,
    ]
    provider.driver.ex_create_public_ip.return_value = public_ip
    _configure_public_ip_mocks(provider, public_ip)
    provider.driver.ex_get_public_ip.return_value = public_ip
    provider.driver.ex_update_nic_properties.side_effect = RuntimeError(
        "Simulated NIC update failure"
    )

    with pytest.raises(VMProviderError, match="Simulated NIC update failure"):
        provider.assign_floating_ip("test-vm")

    assert provider.driver.ex_get_nic.call_count >= 2
    provider.driver.ex_delete_public_ip.assert_not_called()


def test_cleanup_returns_false_when_azure_deletion_fails():
    """Cleanup must not report success when Azure refuses deletion."""
    provider = AzureProvider.__new__(AzureProvider)
    provider.cloud_name = "azure"
    provider.driver = MagicMock()

    nic_id = (
        "/subscriptions/sub-test/resourceGroups/rg-test/"
        "providers/Microsoft.Network/networkInterfaces/nic-existing"
    )
    public_ip_id = (
        "/subscriptions/sub-test/resourceGroups/rg-test/"
        "providers/Microsoft.Network/publicIPAddresses/pip-test"
    )

    nic = SimpleNamespace(
        id=nic_id,
        extra={
            "ipConfigurations": [
                {
                    "name": "primary",
                    "properties": {
                        "subnet": {"id": "subnet-123"},
                    },
                }
            ]
        },
    )

    public_ip = SimpleNamespace(
        id=public_ip_id,
        name="pip-test",
        extra={"ipAddress": "203.0.113.10"},
    )

    provider.driver.ex_get_nic.return_value = nic
    provider.driver.ex_get_public_ip.return_value = public_ip
    provider.driver.ex_delete_public_ip.return_value = False

    result = provider._cleanup_unassociated_public_ip(
        public_ip,
        nic_id,
    )

    assert result is False
    provider.driver.ex_delete_public_ip.assert_called_once_with(public_ip)
