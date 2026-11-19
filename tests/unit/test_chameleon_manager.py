from unittest.mock import MagicMock, patch, mock_open, PropertyMock

import pytest

from cloudmesh.ai.vm.openstack.ChameleonManager import Provider
from cloudmesh.ai.vm.exceptions import VMProviderError
from keystoneauth1.exceptions.catalog import EndpointNotFound


@pytest.fixture
def mock_config():
    return {
        "clouds": {
            "chameleon": {
                "site": "kvm@tacc",
                "project_name": "test-project",
                "auth_url": "https://api.tacc.chameleoncloud.org/v3",
                "username": "test-user",
                "password": "test-password",
                "domain_name": "Default",
            }
        }
    }


@pytest.fixture
def provider(mock_config):
    # We must patch all the references that ChameleonManager imports from chi
    # Using patch.start() to ensure the mocks are active during the Provider's lifecycle
    # Only patch the top‑level ``chi`` reference and the authentication shim.
    # The inner ``chi`` sub‑modules (server, lease, network, ...) are accessed
    # via attributes on the patched ``chi`` MagicMock, so separate patches are
    # unnecessary and cause attribute errors after we removed the direct imports.
    patchers = [
        patch("cloudmesh.ai.vm.openstack.ChameleonManager.chi"),
        patch("cloudmesh.ai.vm.openstack.ChameleonManager.authenticate_chi_from_cloud"),
    ]

    mocks = [p.start() for p in patchers]
    mock_chi = mocks[0]

    # Configure basic defaults for the mock_chi to avoid common attribute errors
    mock_chi.get.side_effect = lambda key: {
        "site": "kvm@tacc",
        "project_name": "test-project",
        "project_id": "proj-123",
        "user_id": "user-456",
        "allocation": "1000 SU",
    }.get(key)

    # ---------------------------------------------------------------------
    # Prepare a dummy ``openstack`` module to avoid importing the real SDK.
    # This dummy module provides a ``connect`` function that returns a MagicMock
    # with a ``compute`` attribute that raises ``EndpointNotFound`` when accessed.
    # The mock also supplies minimal ``session.auth`` and other network attributes
    # used by the provider code.
    # ---------------------------------------------------------------------
    import sys
    import types
    mock_conn = MagicMock()
    # Simulate missing compute endpoint by making ``compute`` a property that raises.
    type(mock_conn).compute = PropertyMock(
        side_effect=EndpointNotFound(
            "publicURL endpoint for compute service in KVM@TACC region not found"
        )
    )
    # Provide stub attributes accessed by the provider
    mock_conn.session = MagicMock()
    mock_conn.session.auth = MagicMock()
    # Provide mock network attributes accessed later in the start flow.
    mock_conn.network = MagicMock()
    mock_conn.network.ports.return_value = []
    mock_conn.network.floating_ips.return_value = []

    dummy_openstack = types.ModuleType("openstack")
    dummy_openstack.connect = MagicMock(return_value=mock_conn)
    # Ensure the dummy module appears in ``sys.modules`` before any import.
    sys.modules["openstack"] = dummy_openstack

    # Provide basic chi.server attributes required by Provider.start.
    mock_chi.server = MagicMock()
    mock_chi.server.list_keypair.return_value = []
    mock_chi.server.update_keypair.return_value = True
    # get_server should return ``None`` to indicate the VM does not already exist.
    mock_chi.server.get_server.return_value = None

    try:
        p = Provider(mock_config, cloud_name="chameleon")
        yield p
    finally:
        # Clean up the dummy module to avoid side‑effects for other tests.
        sys.modules.pop("openstack", None)
        for p in reversed(patchers):
            p.stop()


def test_list_regions(provider):
    with patch("cloudmesh.ai.vm.openstack.ChameleonManager.chi") as mock_chi:
        mock_chi.context.list_sites.return_value = {
            "kvm@tacc": {"description": "TACC KVM site", "status": "active"},
            "kvm@clemson": {"description": "Clemson KVM site", "status": "active"},
        }

        regions = provider.list_regions()

        assert isinstance(regions, list)
        assert len(regions) >= 1
        tacc_region = next((r for r in regions if r["name"] == "kvm@tacc"), None)
        assert tacc_region is not None
        assert tacc_region["description"] == "TACC KVM site"


def test_create_reservation_success(provider):
    with patch("cloudmesh.ai.vm.openstack.ChameleonManager.chi") as mock_chi:
        mock_chi.lease.lease_duration.return_value = ("2026-10-06", "2026-10-07")
        # Mock the lease object returned by create_lease
        mock_lease = MagicMock()
        mock_lease.id = "lease-123"
        mock_chi.lease.create_lease.return_value = mock_lease

        result = provider.create_reservation(
            name="smoke-reservation", node_type="bare_metal", count=1, duration=1
        )

        assert result == "lease-123"


def test_create_reservation_no_project(provider):
    provider.config["clouds"]["chameleon"]["project_name"] = None

    result = provider.create_reservation(
        name="smoke-reservation", node_type="bare_metal", count=1
    )

    assert result is None


def test_get_account_info_success(provider):
    # The provider fixture already configures mock_chi.get
    info = provider.get_account_info()

    assert info["site"] == "kvm@tacc"
    assert info["project_name"] == "test-project"
    assert info["project_id"] == "proj-123"
    assert info["user_id"] == "user-456"
    assert info["allocation"] == "1000 SU"


def test_start_compute_endpoint_missing(provider):
    """Ensure that a missing compute endpoint is detected early and raises a clear error.

    The provider should attempt to validate the OpenStack SDK connection before
    performing any key‑pair operations. When the compute service endpoint is not
    available, ``VMProviderError`` with a helpful hint must be raised.
    """
    # Ensure a key path is defined and mock the file read for the public key.
    provider.config["clouds"]["chameleon"]["key_path"] = "/tmp/fake.pub"

    # Mock the chi server calls to avoid unrelated failures.
    import cloudmesh.ai.vm.openstack.ChameleonManager as cm
    cm.chi.server.list_keypair.return_value = []

    # Patch "open" to return a dummy public key. The dummy ``openstack`` module
    # (injected by the ``provider`` fixture) already raises ``EndpointNotFound``
    # for the compute service, so we only need to patch the file read.
    with patch("builtins.open", mock_open(read_data="ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCtest")):
        with pytest.raises(VMProviderError) as excinfo:
            provider.start(name="test-vm")

        # The raised error should contain a concise hint about the compute
        # endpoint configuration.
        assert "Compute service endpoint not found" in str(excinfo.value)

def test_delete_vm_and_exclusive_lease_success(provider):
    """Delete the exact VM and release its exclusive lease."""
    import cloudmesh.ai.vm.openstack.ChameleonManager as cm

    server = MagicMock()
    server.id = "vm-123"
    server.name = "test-vm"
    server.get_metadata.return_value = {
        "cloudmesh_lease_id": "lease-123"
    }

    lease = MagicMock()
    lease.id = "lease-123"
    lease.name = "res-test-vm"
    lease.flavor_reservations = [
        {
            "id": "reservation-123",
            "resource_type": "flavor:instance",
            "amount": 1,
        }
    ]
    lease.device_reservations = []
    lease.node_reservations = []
    lease.fip_reservations = []
    lease.network_reservations = []

    cm.chi.server.list_servers.side_effect = [[server], [], []]
    cm.chi.lease.get_lease.return_value = lease

    with (
        patch.object(provider, "_setup_chi_context"),
        patch.object(provider, "release_floating_ip"),
    ):
        result = provider.delete("test-vm")

    assert result is True
    cm.chi.server.delete_server.assert_called_once_with("vm-123")
    cm.chi.lease.get_lease.assert_called_once_with("lease-123")
    lease.delete.assert_called_once()


def test_delete_vm_without_lease_metadata(provider):
    """Delete a legacy VM without guessing or deleting a lease."""
    import cloudmesh.ai.vm.openstack.ChameleonManager as cm

    server = MagicMock()
    server.id = "vm-legacy"
    server.name = "legacy-vm"
    server.get_metadata.return_value = {}

    cm.chi.server.list_servers.side_effect = [[server], []]

    with (
        patch.object(provider, "_setup_chi_context"),
        patch.object(provider, "release_floating_ip"),
    ):
        result = provider.delete("legacy-vm")

    assert result is True
    cm.chi.server.delete_server.assert_called_once_with("vm-legacy")
    cm.chi.lease.get_lease.assert_not_called()


def test_delete_vm_preserves_shared_lease(provider):
    """Never release a lease referenced by another existing VM."""
    import cloudmesh.ai.vm.openstack.ChameleonManager as cm

    target = MagicMock()
    target.id = "vm-123"
    target.name = "target-vm"
    target.get_metadata.return_value = {
        "cloudmesh_lease_id": "lease-shared"
    }

    other = MagicMock()
    other.id = "vm-456"
    other.name = "other-vm"
    other.get_metadata.return_value = {
        "cloudmesh_lease_id": "lease-shared"
    }

    lease = MagicMock()
    lease.id = "lease-shared"
    lease.name = "res-target-vm"
    lease.flavor_reservations = [
        {"id": "reservation-123", "amount": 1}
    ]
    lease.device_reservations = []
    lease.node_reservations = []
    lease.fip_reservations = []
    lease.network_reservations = []

    cm.chi.server.list_servers.side_effect = [
        [target, other],
        [other],
        [other],
    ]
    cm.chi.lease.get_lease.return_value = lease

    with (
        patch.object(provider, "_setup_chi_context"),
        patch.object(provider, "release_floating_ip"),
    ):
        with pytest.raises(VMProviderError, match="still associated"):
            provider.delete("target-vm")

    cm.chi.server.delete_server.assert_called_once_with("vm-123")
    lease.delete.assert_not_called()


def test_delete_vm_failure_preserves_lease(provider):
    """Preserve the lease when Nova rejects the VM deletion request."""
    import cloudmesh.ai.vm.openstack.ChameleonManager as cm

    server = MagicMock()
    server.id = "vm-123"
    server.name = "test-vm"
    server.get_metadata.return_value = {
        "cloudmesh_lease_id": "lease-123"
    }

    cm.chi.server.list_servers.return_value = [server]
    cm.chi.server.delete_server.side_effect = RuntimeError(
        "Nova deletion failed"
    )

    with (
        patch.object(provider, "_setup_chi_context"),
        patch.object(provider, "release_floating_ip"),
    ):
        with pytest.raises(VMProviderError, match="Nova deletion failed"):
            provider.delete("test-vm")

    cm.chi.server.delete_server.assert_called_once_with("vm-123")
    cm.chi.lease.get_lease.assert_not_called()


def test_delete_vm_timeout_preserves_lease(provider):
    """Preserve the lease when VM deletion cannot be confirmed."""
    import cloudmesh.ai.vm.openstack.ChameleonManager as cm

    server = MagicMock()
    server.id = "vm-123"
    server.name = "test-vm"
    server.get_metadata.return_value = {
        "cloudmesh_lease_id": "lease-123"
    }

    cm.chi.server.list_servers.return_value = [server]

    with (
        patch.object(provider, "_setup_chi_context"),
        patch.object(provider, "release_floating_ip"),
        patch.object(
            provider, "_wait_for_server_deletion", return_value=False
        ) as wait_mock,
    ):
        with pytest.raises(VMProviderError, match="Timed out"):
            provider.delete("test-vm")

    cm.chi.server.delete_server.assert_called_once_with("vm-123")
    wait_mock.assert_called_once_with("vm-123")
    cm.chi.lease.get_lease.assert_not_called()


def test_delete_vm_lease_cleanup_failure(provider):
    """Report partial failure when VM deletion succeeds but lease cleanup fails."""
    import cloudmesh.ai.vm.openstack.ChameleonManager as cm

    server = MagicMock()
    server.id = "vm-123"
    server.name = "test-vm"
    server.get_metadata.return_value = {
        "cloudmesh_lease_id": "lease-123"
    }

    lease = MagicMock()
    lease.id = "lease-123"
    lease.name = "res-test-vm"
    lease.flavor_reservations = [
        {"id": "reservation-123", "amount": 1}
    ]
    lease.device_reservations = []
    lease.node_reservations = []
    lease.fip_reservations = []
    lease.network_reservations = []
    lease.delete.side_effect = RuntimeError("Blazar unavailable")

    cm.chi.server.list_servers.side_effect = [[server], [], []]
    cm.chi.lease.get_lease.return_value = lease

    with (
        patch.object(provider, "_setup_chi_context"),
        patch.object(provider, "release_floating_ip"),
    ):
        with pytest.raises(VMProviderError, match="Blazar unavailable"):
            provider.delete("test-vm")

    cm.chi.server.delete_server.assert_called_once_with("vm-123")
    lease.delete.assert_called_once()


def test_delete_vm_without_server_id_preserves_lease(provider):
    """Never delete a VM or release its lease without a valid server ID."""
    import cloudmesh.ai.vm.openstack.ChameleonManager as cm

    server = MagicMock()
    server.id = None
    server.name = "test-vm"
    server.get_metadata.return_value = {
        "cloudmesh_lease_id": "lease-123"
    }

    cm.chi.server.list_servers.return_value = [server]

    with (
        patch.object(provider, "_setup_chi_context"),
        patch.object(provider, "release_floating_ip"),
    ):
        with pytest.raises(VMProviderError, match="server ID is unavailable"):
            provider.delete("test-vm")

    cm.chi.server.delete_server.assert_not_called()
    server.delete.assert_not_called()
    cm.chi.lease.get_lease.assert_not_called()


def test_delete_preserves_lease_when_legacy_vm_exists(provider):
    """Unknown ownership on another VM must prevent lease cleanup."""
    import cloudmesh.ai.vm.openstack.ChameleonManager as cm

    target = MagicMock()
    target.id = "server-123"
    target.name = "test-vm"
    target.get_metadata.return_value = {
        "cloudmesh_lease_id": "lease-123"
    }

    legacy = MagicMock()
    legacy.id = "server-legacy"
    legacy.name = "legacy-vm"
    legacy.get_metadata.return_value = {}

    lease = MagicMock()
    lease.id = "lease-123"
    lease.name = "res-test-vm"
    lease.flavor_reservations = [{"id": "reservation-123", "amount": 1}]

    cm.chi.server.list_servers.side_effect = [
        [target, legacy],
        [legacy],
        [legacy],
    ]
    cm.chi.lease.get_lease.return_value = lease

    with (
        patch.object(provider, "_setup_chi_context"),
        patch.object(provider, "release_floating_ip"),
    ):
        with pytest.raises(VMProviderError, match="lease metadata is missing"):
            provider.delete("test-vm")

    cm.chi.server.delete_server.assert_called_once_with("server-123")
    lease.delete.assert_not_called()


def test_delete_releases_lease_with_unrelated_tagged_vm(provider):
    """A VM with a different lease ID must not block cleanup."""
    import cloudmesh.ai.vm.openstack.ChameleonManager as cm

    target = MagicMock()
    target.id = "server-123"
    target.name = "test-vm"
    target.get_metadata.return_value = {
        "cloudmesh_lease_id": "lease-123"
    }

    unrelated = MagicMock()
    unrelated.id = "server-other"
    unrelated.name = "other-vm"
    unrelated.get_metadata.return_value = {
        "cloudmesh_lease_id": "lease-other"
    }

    lease = MagicMock()
    lease.id = "lease-123"
    lease.name = "res-test-vm"
    lease.flavor_reservations = [{"id": "reservation-123", "amount": 1}]
    lease.device_reservations = []
    lease.node_reservations = []
    lease.fip_reservations = []
    lease.network_reservations = []

    cm.chi.server.list_servers.side_effect = [
        [target, unrelated],
        [unrelated],
        [unrelated],
    ]
    cm.chi.lease.get_lease.return_value = lease

    with (
        patch.object(provider, "_setup_chi_context"),
        patch.object(provider, "release_floating_ip"),
    ):
        assert provider.delete("test-vm") is True

    cm.chi.server.delete_server.assert_called_once_with("server-123")
    lease.delete.assert_called_once_with()


@pytest.fixture
def lease_start_setup(provider, monkeypatch):
    """Prepare Provider.start() for isolated lease tests."""
    import cloudmesh.ai.vm.openstack.ChameleonManager as cm
    from cloudmesh.ai.vm.openstack.OpenstackManager import OpenstackManager

    monkeypatch.delenv("CLOUDMESH_CHAMELEON_MOCK", raising=False)

    provider.config["clouds"]["chameleon"].update({
        "key_path": "/tmp/test-chameleon-key.pub",
        "image": "test-image",
        "flavor": "test-flavor",
    })

    connection = MagicMock()
    connection.compute = MagicMock()

    monkeypatch.setattr(
        OpenstackManager,
        "_get_sdk_conn",
        lambda self: connection,
    )

    cm.chi.server.list_keypair.return_value = []
    cm.chi.server.get_server.return_value = None
    cm.chi.server.get_flavor_id.return_value = "flavor-123"

    with (
        patch.object(provider, "_setup_chi_context"),
        patch("builtins.open", mock_open(read_data="ssh-rsa TESTKEY")),
    ):
        yield cm


def test_start_rejects_existing_active_lease(provider, lease_start_setup):
    """An active lease must not be reused for a new VM."""
    cm = lease_start_setup

    existing = MagicMock()
    existing.name = "res-test-vm"
    existing.id = "existing-lease"
    existing.status = "ACTIVE"

    cm.chi.lease.list_leases.return_value = [existing]

    with pytest.raises(VMProviderError, match="Refusing to reuse"):
        provider.start(name="test-vm")

    cm.chi.lease.Lease.assert_not_called()


def test_start_rejects_existing_pending_lease(provider, lease_start_setup):
    """Pending reservations must also be protected."""
    cm = lease_start_setup

    existing = MagicMock()
    existing.name = "res-test-vm"
    existing.id = "pending-lease"
    existing.status = "PENDING"

    cm.chi.lease.list_leases.return_value = [existing]

    with pytest.raises(VMProviderError, match="Refusing to reuse"):
        provider.start(name="test-vm")

    cm.chi.lease.Lease.assert_not_called()


def test_start_allows_terminated_lease_name(provider, lease_start_setup):
    """A terminated lease must not trigger the active-lease conflict."""
    cm = lease_start_setup

    existing = MagicMock()
    existing.name = "res-test-vm"
    existing.id = "old-lease"
    existing.status = "TERMINATED"

    cm.chi.lease.list_leases.return_value = [existing]

    lease = cm.chi.lease.Lease.return_value
    lease.id = "new-lease"
    lease.flavor_reservations = [{"id": "reservation-123"}]

    server = cm.chi.server.Server.return_value
    server.id = "server-123"

    provider.start(name="test-vm", assign_ip=False)

    lease.submit.assert_called_once_with(idempotent=False)
    server.set_metadata_item.assert_called_once_with(
        "cloudmesh_lease_id", "new-lease"
    )


def test_start_lease_listing_failure_blocks_creation(provider, lease_start_setup):
    """Blazar errors must never be interpreted as an empty lease list."""
    cm = lease_start_setup

    cm.chi.lease.list_leases.side_effect = RuntimeError(
        "Blazar API unavailable"
    )

    with pytest.raises(Exception, match="Blazar API unavailable"):
        provider.start(name="test-vm")

    cm.chi.lease.Lease.assert_not_called()


def test_start_metadata_failure_preserves_resources(provider, lease_start_setup):
    """Metadata failure must report resources without deleting them."""
    cm = lease_start_setup

    cm.chi.lease.list_leases.return_value = []

    lease = cm.chi.lease.Lease.return_value
    lease.id = "lease-123"
    lease.flavor_reservations = [{"id": "reservation-123"}]

    server = cm.chi.server.Server.return_value
    server.id = "server-123"
    server.set_metadata_item.side_effect = RuntimeError(
        "Nova metadata API unavailable"
    )

    with pytest.raises(VMProviderError) as excinfo:
        provider.start(name="test-vm", assign_ip=False)

    message = str(excinfo.value)

    assert "server-123" in message
    assert "lease-123" in message
    assert "Inspect Chameleon resources before retrying" in message

    server.set_metadata_item.assert_called_once_with(
        "cloudmesh_lease_id", "lease-123"
    )
    cm.chi.server.delete_server.assert_not_called()
    lease.delete.assert_not_called()


def test_delete_aborts_when_server_listing_unavailable(provider):
    """Never attempt VM deletion when the server listing is unavailable."""
    import cloudmesh.ai.vm.openstack.ChameleonManager as cm

    cm.chi.server.list_servers.return_value = None

    with patch.object(provider, "_setup_chi_context"):
        with pytest.raises(
            VMProviderError,
            match="Unable to retrieve Chameleon server listing",
        ):
            provider.delete("test-vm")

    cm.chi.server.delete_server.assert_not_called()
    cm.chi.lease.get_lease.assert_not_called()


def test_delete_preserves_lease_with_malformed_flavor_reservation(provider):
    """Malformed reservation data must never trigger lease deletion."""
    import cloudmesh.ai.vm.openstack.ChameleonManager as cm

    server = MagicMock()
    server.id = "server-123"
    server.name = "test-vm"
    server.get_metadata.return_value = {
        "cloudmesh_lease_id": "lease-123"
    }

    lease = MagicMock()
    lease.id = "lease-123"
    lease.name = "res-test-vm"
    lease.flavor_reservations = ["invalid-reservation"]

    cm.chi.server.list_servers.side_effect = [
        [server],
        [],
        [],
    ]
    cm.chi.lease.get_lease.return_value = lease

    with (
        patch.object(provider, "_setup_chi_context"),
        patch.object(provider, "release_floating_ip"),
    ):
        with pytest.raises(
            VMProviderError,
            match="does not have an exclusive single-instance",
        ):
            provider.delete("test-vm")

    cm.chi.server.delete_server.assert_called_once_with("server-123")
    lease.delete.assert_not_called()
