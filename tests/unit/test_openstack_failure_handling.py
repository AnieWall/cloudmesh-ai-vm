"""Regression tests for OpenStack failure handling (issue #103)."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from cloudmesh.ai.vm.exceptions import VMProviderError
from cloudmesh.ai.vm.openstack.OpenstackManager import OpenstackManager


@pytest.fixture
def provider():
    return OpenstackManager(
        {
            "clouds": {
                "test-openstack": {
                    "image": "test-image",
                    "flavor": "test-flavor",
                    "security_group": "ssh-access",
                    "network": "test-network",
                }
            }
        },
        cloud_name="test-openstack",
    )


def test_start_server_creation_failure(provider):
    """An SDK creation failure must raise without deleting an unrelated VM."""
    conn = MagicMock()

    conn.compute.find_image.return_value = SimpleNamespace(
        id="image-123", name="test-image"
    )
    conn.compute.find_flavor.return_value = SimpleNamespace(
        id="flavor-123", name="test-flavor"
    )
    conn.network.find_security_group.return_value = SimpleNamespace(
        id="sg-123", name="ssh-access"
    )

    provider.driver = conn.compute

    conn.compute.create_server.side_effect = RuntimeError(
        "Simulated server creation failure"
    )

    with (
        patch.object(provider, "_get_sdk_conn", return_value=conn),
        patch.object(provider, "_get_default_network", return_value="test-network"),
        pytest.raises(VMProviderError, match="SDK start failed"),
    ):
        provider.start(name="test-vm", assign_ip=False)

    conn.compute.create_server.assert_called_once()
    conn.compute.delete_server.assert_not_called()


def test_start_vm_fails_to_become_active(provider):
    """A VM that never becomes ACTIVE must produce a provider error."""
    conn = MagicMock()
    provider.driver = conn.compute

    conn.compute.find_image.return_value = SimpleNamespace(
        id="image-123", name="test-image"
    )
    conn.compute.find_flavor.return_value = SimpleNamespace(
        id="flavor-123", name="test-flavor"
    )
    conn.compute.find_security_group.return_value = SimpleNamespace(
        id="sg-123", name="ssh-access"
    )
    conn.compute.create_server.return_value = SimpleNamespace(
        id="server-123", name="test-vm"
    )

    with (
        patch.object(provider, "_get_default_network", return_value="test-network"),
        patch.object(provider, "wait_for_active", return_value=False) as wait,
        pytest.raises(VMProviderError, match="failed to become ACTIVE"),
    ):
        provider.start(name="test-vm", assign_ip=False)

    conn.compute.create_server.assert_called_once()
    wait.assert_called_once_with("test-vm")
    conn.compute.delete_server.assert_not_called()


def test_start_activation_failure_preserves_vm_and_reserved_ip(provider):
    """Preserve the failed VM and its reserved IP for troubleshooting."""
    conn = MagicMock()
    provider.driver = conn.compute

    conn.compute.find_image.return_value = SimpleNamespace(
        id="image-123", name="test-image"
    )
    conn.compute.find_flavor.return_value = SimpleNamespace(
        id="flavor-123", name="test-flavor"
    )
    conn.compute.find_security_group.return_value = SimpleNamespace(
        id="sg-123", name="ssh-access"
    )
    conn.compute.create_server.return_value = SimpleNamespace(
        id="server-123", name="test-vm"
    )

    floating_ip = SimpleNamespace(
        id="fip-123",
        floating_ip_address="192.0.2.50",
        port_id=None,
    )

    with (
        patch(
            "cloudmesh.ai.vm.fip_utils.list_unassigned_fips",
            return_value=[],
        ),
        patch(
            "cloudmesh.ai.vm.fip_utils.allocate_fip_with_retry",
            return_value=floating_ip,
        ) as allocate,
        patch(
            "cloudmesh.ai.vm.fip_utils.release_fip"
        ) as release,
        patch.object(
            provider, "_get_default_network", return_value="test-network"
        ),
        patch.object(provider, "wait_for_active", return_value=False),
        pytest.raises(VMProviderError, match="failed to become ACTIVE"),
    ):
        provider.start(name="test-vm", assign_ip=True)

    allocate.assert_called_once()
    conn.compute.create_server.assert_called_once()
    conn.compute.delete_server.assert_not_called()
    release.assert_not_called()



def test_start_creation_failure_preserves_reused_floating_ip(provider):
    """A pre-existing floating IP must not be deleted on provisioning failure."""
    conn = MagicMock()
    provider.driver = conn.compute

    existing_fip = SimpleNamespace(
        id="existing-fip-123",
        floating_ip_address="192.0.2.50",
        port_id=None,
    )

    conn.compute.find_image.return_value = SimpleNamespace(
        id="image-123", name="test-image"
    )
    conn.compute.find_flavor.return_value = SimpleNamespace(
        id="flavor-123", name="test-flavor"
    )
    conn.compute.find_security_group.return_value = SimpleNamespace(
        id="sg-123", name="ssh-access"
    )
    conn.compute.create_server.side_effect = RuntimeError(
        "Simulated server creation failure"
    )

    with (
        patch(
            "cloudmesh.ai.vm.fip_utils.list_unassigned_fips",
            return_value=[existing_fip],
        ),
        patch(
            "cloudmesh.ai.vm.fip_utils.release_fip"
        ) as release,
        patch.object(
            provider, "_get_default_network", return_value="test-network"
        ),
        pytest.raises(VMProviderError, match="SDK start failed"),
    ):
        provider.start(name="test-vm", assign_ip=True)

    conn.compute.create_server.assert_called_once()
    conn.compute.delete_server.assert_not_called()
    release.assert_not_called()


def test_start_creation_failure_releases_new_floating_ip_once(provider):
    """A newly allocated floating IP must be released exactly once."""
    conn = MagicMock()
    provider.driver = conn.compute

    new_fip = SimpleNamespace(
        id="new-fip-123",
        floating_ip_address="192.0.2.60",
        port_id=None,
    )

    conn.compute.find_image.return_value = SimpleNamespace(
        id="image-123", name="test-image"
    )
    conn.compute.find_flavor.return_value = SimpleNamespace(
        id="flavor-123", name="test-flavor"
    )
    conn.compute.find_security_group.return_value = SimpleNamespace(
        id="sg-123", name="ssh-access"
    )
    conn.compute.create_server.side_effect = RuntimeError(
        "Simulated server creation failure"
    )

    with (
        patch(
            "cloudmesh.ai.vm.fip_utils.list_unassigned_fips",
            return_value=[],
        ),
        patch(
            "cloudmesh.ai.vm.fip_utils.allocate_fip_with_retry",
            return_value=new_fip,
        ) as allocate,
        patch(
            "cloudmesh.ai.vm.fip_utils.release_fip"
        ) as release,
        patch.object(
            provider, "_get_default_network", return_value="test-network"
        ),
        pytest.raises(VMProviderError, match="SDK start failed"),
    ):
        provider.start(name="test-vm", assign_ip=True)

    allocate.assert_called_once()
    conn.compute.create_server.assert_called_once()
    conn.compute.delete_server.assert_not_called()
    release.assert_called_once()
    cleanup_conn, cleanup_fip = release.call_args.args
    assert cleanup_fip is new_fip
    assert cleanup_conn.compute is conn.compute
    assert cleanup_conn.network is conn.compute


def test_start_attachment_failure_preserves_vm_and_reused_ip(provider):
    """Failed attachment must preserve the VM and reused floating IP."""
    conn = MagicMock()
    provider.driver = conn.compute

    existing_fip = SimpleNamespace(
        id="existing-fip-123",
        floating_ip_address="192.0.2.50",
        port_id=None,
    )

    conn.compute.find_image.return_value = SimpleNamespace(
        id="image-123", name="test-image"
    )
    conn.compute.find_flavor.return_value = SimpleNamespace(
        id="flavor-123", name="test-flavor"
    )
    conn.compute.find_security_group.return_value = SimpleNamespace(
        id="sg-123", name="ssh-access"
    )
    conn.compute.create_server.return_value = SimpleNamespace(
        id="server-123", name="test-vm"
    )

    with (
        patch(
            "cloudmesh.ai.vm.fip_utils.list_unassigned_fips",
            return_value=[existing_fip],
        ),
        patch("cloudmesh.ai.vm.fip_utils.release_fip") as release,
        patch.object(
            provider, "_get_default_network", return_value="test-network"
        ),
        patch.object(provider, "wait_for_active", return_value=True),
        patch.object(
            conn.compute,
            "ports",
            return_value=[],
        ) as ports,
        pytest.raises(VMProviderError, match="Failed to assign floating IP"),
    ):
        provider.start(name="test-vm", assign_ip=True)

    ports.assert_called_once_with(device_id="server-123")
    conn.compute.delete_server.assert_not_called()
    release.assert_not_called()


def test_start_attachment_failure_preserves_vm_and_releases_unused_ip(provider):
    """Preserve the VM but release a newly allocated, unattached IP."""
    conn = MagicMock()
    provider.driver = conn.compute

    new_fip = SimpleNamespace(
        id="new-fip-123",
        floating_ip_address="192.0.2.60",
        port_id=None,
    )

    conn.compute.find_image.return_value = SimpleNamespace(
        id="image-123", name="test-image"
    )
    conn.compute.find_flavor.return_value = SimpleNamespace(
        id="flavor-123", name="test-flavor"
    )
    conn.compute.find_security_group.return_value = SimpleNamespace(
        id="sg-123", name="ssh-access"
    )
    conn.compute.create_server.return_value = SimpleNamespace(
        id="server-123", name="test-vm"
    )
    conn.compute.ports.return_value = []

    with (
        patch(
            "cloudmesh.ai.vm.fip_utils.list_unassigned_fips",
            return_value=[],
        ),
        patch(
            "cloudmesh.ai.vm.fip_utils.allocate_fip_with_retry",
            return_value=new_fip,
        ) as allocate,
        patch(
            "cloudmesh.ai.vm.fip_utils.release_fip"
        ) as release,
        patch.object(
            provider, "_get_default_network", return_value="test-network"
        ),
        patch.object(provider, "wait_for_active", return_value=True),
        pytest.raises(VMProviderError, match="Failed to assign floating IP"),
    ):
        provider.start(name="test-vm", assign_ip=True)

    allocate.assert_called_once()
    conn.compute.ports.assert_called_once_with(device_id="server-123")
    conn.compute.delete_server.assert_not_called()

    release.assert_called_once()
    cleanup_conn, cleanup_fip = release.call_args.args
    assert cleanup_fip is new_fip
    assert cleanup_conn.compute is conn.compute
    assert cleanup_conn.network is conn.compute


def test_stop_sdk_failure_does_not_delete_vm(provider):
    """A failed shutdown must raise an error without deleting the VM."""
    conn = MagicMock()
    server = SimpleNamespace(
        id="server-123",
        name="test-vm",
        status="ACTIVE",
    )

    conn.compute.stop_server.side_effect = RuntimeError(
        "Simulated OpenStack shutdown failure"
    )

    with (
        patch.object(provider, "exists", return_value=True),
        patch.object(provider, "_find_node", return_value=server),
        patch.object(provider, "_get_sdk_conn", return_value=conn),
        pytest.raises(VMProviderError, match="SDK stop failed"),
    ):
        provider.stop("test-vm")

    conn.compute.stop_server.assert_called_once_with(server)
    conn.compute.delete_server.assert_not_called()


def test_stop_sdk_failure_does_not_expose_credentials(provider, caplog):
    """SDK shutdown errors must not expose credentials in public errors."""
    conn = MagicMock()
    server = SimpleNamespace(
        id="server-123",
        name="test-vm",
        status="ACTIVE",
    )
    secret = "test-secret-token-123"

    conn.compute.stop_server.side_effect = RuntimeError(
        f"Authentication failed with token {secret}"
    )

    with (
        patch.object(provider, "exists", return_value=True),
        patch.object(provider, "_find_node", return_value=server),
        patch.object(provider, "_get_sdk_conn", return_value=conn),
        pytest.raises(VMProviderError) as exc_info,
    ):
        provider.stop("test-vm")

    assert "SDK stop failed" in str(exc_info.value)
    assert "Authentication failed with token [REDACTED]" in str(exc_info.value)
    assert secret not in str(exc_info.value)
    assert secret not in caplog.text
    conn.compute.stop_server.assert_called_once_with(server)


def test_delete_sdk_failure_does_not_report_success(provider):
    """An SDK deletion failure must raise rather than report success."""
    conn = MagicMock()
    server = SimpleNamespace(
        id="server-123",
        name="test-vm",
        status="ACTIVE",
    )

    conn.compute.delete_server.side_effect = RuntimeError(
        "Simulated OpenStack deletion failure"
    )

    with (
        patch.object(provider, "exists", return_value=True),
        patch.object(provider, "release_floating_ip") as release,
        patch.object(provider, "_find_node", return_value=server),
        patch.object(provider, "_get_sdk_conn", return_value=conn),
        pytest.raises(VMProviderError, match="SDK delete failed"),
    ):
        provider.delete("test-vm")

    release.assert_not_called()
    conn.compute.delete_server.assert_called_once_with(server)


def test_delete_sdk_failure_does_not_expose_credentials(provider, caplog):
    """SDK deletion failures must not expose credentials in errors or logs."""
    conn = MagicMock()
    server = SimpleNamespace(
        id="server-123",
        name="test-vm",
        status="ACTIVE",
    )
    secret = "test-delete-secret-token-123"

    conn.compute.delete_server.side_effect = RuntimeError(
        f"Authentication failed with token {secret}"
    )

    with (
        patch.object(provider, "exists", return_value=True),
        patch.object(provider, "release_floating_ip"),
        patch.object(provider, "_find_node", return_value=server),
        patch.object(provider, "_get_sdk_conn", return_value=conn),
        pytest.raises(VMProviderError) as exc_info,
    ):
        provider.delete("test-vm")

    assert "SDK delete failed" in str(exc_info.value)
    assert "Authentication failed with token [REDACTED]" in str(exc_info.value)
    assert secret not in str(exc_info.value)
    assert secret not in caplog.text
    conn.compute.delete_server.assert_called_once_with(server)


def test_delete_sdk_failure_preserves_floating_ip(provider):
    """A failed VM deletion must not release its floating IP."""
    conn = MagicMock()
    server = SimpleNamespace(
        id="server-123",
        name="test-vm",
        status="ACTIVE",
    )

    conn.compute.delete_server.side_effect = RuntimeError(
        "Simulated deletion failure"
    )

    with (
        patch.object(provider, "exists", return_value=True),
        patch.object(provider, "release_floating_ip") as release,
        patch.object(provider, "_find_node", return_value=server),
        patch.object(provider, "_get_sdk_conn", return_value=conn),
        pytest.raises(VMProviderError, match="SDK delete failed"),
    ):
        provider.delete("test-vm")

    conn.compute.delete_server.assert_called_once_with(server)
    release.assert_not_called()


def test_delete_timeout_preserves_floating_ip(provider):
    """A deletion timeout must preserve the floating IP for review."""
    from openstack.exceptions import ResourceTimeout

    conn = MagicMock()
    server = SimpleNamespace(
        id="server-123",
        name="test-vm",
        status="ACTIVE",
    )

    conn.compute.wait_for_delete.side_effect = ResourceTimeout(
        "Simulated VM deletion timeout"
    )

    with (
        patch.object(provider, "exists", return_value=True),
        patch.object(provider, "release_floating_ip") as release,
        patch.object(provider, "_find_node", return_value=server),
        patch.object(provider, "_get_sdk_conn", return_value=conn),
        pytest.raises(VMProviderError, match="SDK delete failed"),
    ):
        provider.delete("test-vm")

    conn.compute.delete_server.assert_called_once_with(server)
    conn.compute.wait_for_delete.assert_called_once_with(
        server, interval=2, wait=120
    )
    release.assert_not_called()



def test_delete_success_releases_original_floating_ip(provider):
    """Successful deletion must release the VM's original floating IP."""
    conn = MagicMock()
    server = SimpleNamespace(
        id="server-123",
        name="test-vm",
        status="ACTIVE",
        public_ips=["192.0.2.50"],
    )
    floating_ip = SimpleNamespace(
        id="fip-123",
        floating_ip_address="192.0.2.50",
        port_id="port-123",
    )

    conn.network.find_floating_ip.return_value = floating_ip
    conn.network.get_port.return_value = SimpleNamespace(
        id="port-123",
        device_id="server-123",
    )

    # Once deletion completes, the VM can no longer be found.
    def find_node(name):
        if conn.compute.wait_for_delete.called:
            return None
        return server

    with (
        patch.object(provider, "exists", return_value=True),
        patch.object(provider, "_find_node", side_effect=find_node),
        patch.object(provider, "_get_sdk_conn", return_value=conn),
    ):
        assert provider.delete("test-vm") is True

    conn.compute.delete_server.assert_called_once_with(server)
    conn.compute.wait_for_delete.assert_called_once_with(
        server, interval=2, wait=120
    )
    conn.network.find_floating_ip.assert_called_with("192.0.2.50")
    conn.network.delete_floating_ip.assert_called_once_with(floating_ip)


def test_delete_preserves_floating_ip_attached_to_another_vm(provider):
    """VM deletion must not release an IP attached to another server."""
    conn = MagicMock()
    server = SimpleNamespace(
        id="server-123",
        name="test-vm",
        status="ACTIVE",
        public_ips=["192.0.2.50"],
    )
    floating_ip = SimpleNamespace(
        id="fip-123",
        floating_ip_address="192.0.2.50",
        port_id="other-server-port",
    )
    port = SimpleNamespace(
        id="other-server-port",
        device_id="other-server-456",
    )

    conn.network.find_floating_ip.return_value = floating_ip
    conn.network.get_port.return_value = port

    with (
        patch.object(provider, "exists", return_value=True),
        patch.object(provider, "_find_node", return_value=server),
        patch.object(provider, "_get_sdk_conn", return_value=conn),
    ):
        assert provider.delete("test-vm") is True

    conn.compute.delete_server.assert_called_once_with(server)
    conn.compute.wait_for_delete.assert_called_once_with(
        server, interval=2, wait=120
    )
    conn.network.delete_floating_ip.assert_not_called()


def test_delete_floating_ip_cleanup_failure_is_reported(provider, caplog):
    """A failed IP cleanup must be reported without leaking SDK secrets."""
    conn = MagicMock()
    server = SimpleNamespace(
        id="server-123",
        name="test-vm",
        status="ACTIVE",
        public_ips=["192.0.2.50"],
    )
    floating_ip = SimpleNamespace(
        id="fip-123",
        floating_ip_address="192.0.2.50",
        port_id="port-123",
    )
    secret = "test-cleanup-secret-123"

    conn.network.find_floating_ip.return_value = floating_ip
    conn.network.get_port.return_value = SimpleNamespace(
        id="port-123",
        device_id="server-123",
    )
    conn.network.delete_floating_ip.side_effect = RuntimeError(
        f"Cleanup failed with token {secret}"
    )

    with (
        patch.object(provider, "exists", return_value=True),
        patch.object(provider, "_find_node", return_value=server),
        patch.object(provider, "_get_sdk_conn", return_value=conn),
        pytest.raises(VMProviderError, match="VM deleted successfully.*floating IP cleanup failed") as exc_info,
    ):
        provider.delete("test-vm")

    conn.compute.delete_server.assert_called_once_with(server)
    conn.compute.wait_for_delete.assert_called_once_with(
        server, interval=2, wait=120
    )
    conn.network.delete_floating_ip.assert_called_once_with(floating_ip)

    assert secret not in str(exc_info.value)
    assert secret not in caplog.text

def test_upload_key_missing_file_returns_false(provider, tmp_path):
    """Missing public-key files must not trigger OpenStack API calls."""
    missing_key = tmp_path / "nonexistent-key.pub"

    with patch.object(provider, "_get_sdk_conn") as get_conn:
        result = provider.upload_key(str(missing_key), "test-key")

    assert result is False
    get_conn.assert_not_called()

def test_upload_key_sdk_failure_returns_false(provider, tmp_path):
    """An SDK upload failure must return False and report the error."""
    public_key = tmp_path / "test-key.pub"
    public_key.write_text("ssh-ed25519 AAAATESTKEY test@example.com\n")

    conn = MagicMock()
    conn.compute.create_keypair.side_effect = RuntimeError(
        "Simulated OpenStack keypair creation failure"
    )

    with (
        patch.object(provider, "_get_sdk_conn", return_value=conn),
        patch("cloudmesh.ai.vm.logger.logger.error") as log_error,
    ):
        result = provider.upload_key(str(public_key), "test-key")

    assert result is False
    conn.compute.create_keypair.assert_called_once_with(
        name="test-key",
        public_key="ssh-ed25519 AAAATESTKEY test@example.com",
    )
    log_error.assert_called_once()
    assert "Simulated OpenStack keypair creation failure" in str(
        log_error.call_args
    )

def test_upload_key_already_exists_returns_true(provider, tmp_path):
    """An existing OpenStack keypair should be treated as success."""
    public_key = tmp_path / "test-key.pub"
    public_key.write_text("ssh-ed25519 AAAATESTKEY test@example.com\n")

    conn = MagicMock()
    conn.compute.create_keypair.side_effect = RuntimeError(
        "Keypair test-key already exists"
    )

    with patch.object(provider, "_get_sdk_conn", return_value=conn):
        result = provider.upload_key(str(public_key), "test-key")

    assert result is True
    conn.compute.create_keypair.assert_called_once_with(
        name="test-key",
        public_key="ssh-ed25519 AAAATESTKEY test@example.com",
    )

def test_delete_key_sdk_failure_returns_false(provider):
    """An SDK deletion failure must return False and report the error."""
    conn = MagicMock()
    conn.compute.delete_keypair.side_effect = RuntimeError(
        "Simulated OpenStack keypair deletion failure"
    )

    with (
        patch.object(provider, "_get_sdk_conn", return_value=conn),
        patch("cloudmesh.ai.vm.logger.logger.error") as log_error,
    ):
        result = provider.delete_key("test-key")

    assert result is False
    conn.compute.delete_keypair.assert_called_once_with("test-key")
    log_error.assert_called_once()
    assert "Simulated OpenStack keypair deletion failure" in str(
        log_error.call_args
    )

def test_upload_key_does_not_log_private_key_material(provider, tmp_path):
    """SDK failures must not expose private-key material in logs."""
    public_key = tmp_path / "test-key.pub"
    public_key.write_text("ssh-ed25519 AAAATESTKEY test@example.com\n")

    secret = "SIMULATED_PRIVATE_KEY_PAYLOAD_DO_NOT_LOG"
    private_key = (
        "-----BEGIN OPENSSH PRIVATE KEY-----\n"
        f"{secret}\n"
        "-----END OPENSSH PRIVATE KEY-----"
    )
    conn = MagicMock()
    conn.compute.create_keypair.side_effect = RuntimeError(
        f"OpenStack request rejected: {private_key}"
    )

    with (
        patch.object(provider, "_get_sdk_conn", return_value=conn),
        patch("cloudmesh.ai.vm.logger.logger.error") as log_error,
    ):
        result = provider.upload_key(str(public_key), "test-key")

    assert result is False
    log_error.assert_called_once()

    logged_message = str(log_error.call_args)
    assert secret not in logged_message
    assert "-----BEGIN OPENSSH PRIVATE KEY-----" not in logged_message
    assert "OpenStack request rejected" in logged_message
