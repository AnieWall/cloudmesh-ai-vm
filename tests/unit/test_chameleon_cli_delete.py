"""Mocked CLI regression tests for ``cmx vm delete`` failure handling.

Part of the safety verification for issue #123: requesting deletion of a VM
that does not exist must produce a visible, meaningful failure message, a
non-zero CLI exit code, and must never report a successful deletion.

The provider is fully mocked with ``unittest.mock``; the real cloud service
is never contacted.
"""

import importlib
import os
import sys
import tempfile
from unittest.mock import MagicMock, patch

# ``docker`` is imported by the unrelated container command group that the
# ``cmx`` package loads at import time. It is irrelevant for ``vm delete``
# and may be absent in minimal test environments, so stub it only when it
# cannot be imported.
try:
    importlib.import_module("docker")
except ImportError:
    sys.modules["docker"] = MagicMock()

# Keep the state manager away from the user's real clouds.yaml: the command
# package reads CLOUDMESH_VM_CONFIG at import time.
os.environ["CLOUDMESH_VM_CONFIG"] = os.path.join(
    tempfile.mkdtemp(prefix="cmx_cli_test_"), "clouds.yaml"
)

from click.testing import CliRunner  # noqa: E402

from cloudmesh.ai.command.vm import delete as vm_delete  # noqa: E402


def _mocked_provider(delete_returns: bool) -> MagicMock:
    provider = MagicMock()
    provider.cloud_name = "chameleon"
    provider.delete.return_value = delete_returns
    return provider


def test_cli_delete_nonexistent_vm_reports_failure():
    """Deleting a VM that does not exist must fail loudly with a non-zero
    exit code and never report a successful deletion.
    """
    provider = _mocked_provider(delete_returns=False)

    with patch.object(
        vm_delete, "get_active_provider", return_value=provider
    ), patch.object(vm_delete, "resolve_vms", return_value=["nonexistent-vm"]):
        result = CliRunner().invoke(vm_delete.delete, ["nonexistent-vm"])

    # Non-zero CLI exit code.
    assert result.exit_code != 0
    output = result.output
    # Visible, meaningful failure message naming the requested VM.
    assert "Failed to delete VM nonexistent-vm" in output
    assert "Error:" in output
    # Must never report a successful deletion.
    assert "Successfully deleted VM" not in output
    # The provider was asked exactly once for the requested name.
    provider.delete.assert_called_once_with("nonexistent-vm")


def test_cli_delete_success_behavior_preserved():
    """A successful provider deletion still reports success with exit 0."""
    provider = _mocked_provider(delete_returns=True)

    with patch.object(
        vm_delete, "get_active_provider", return_value=provider
    ), patch.object(vm_delete, "resolve_vms", return_value=["existing-vm"]):
        result = CliRunner().invoke(vm_delete.delete, ["existing-vm"])

    assert result.exit_code == 0
    assert "Successfully deleted VM existing-vm" in result.output
    provider.delete.assert_called_once_with("existing-vm")