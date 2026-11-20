"""Regression tests for VM SSH command failure handling (issue #103)."""

import subprocess
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from cloudmesh.ai.command.vm import cmx


def test_ssh_nonzero_exit_code_reports_failure():
    """A failed SSH process must not be reported as successful."""
    provider = MagicMock()
    provider.cloud_name = "test-openstack"
    provider.info.return_value = {"ip": "192.0.2.10"}

    with (
        patch(
            "cloudmesh.ai.command.vm.ssh.get_active_provider",
            return_value=provider,
        ),
        patch(
            "cloudmesh.ai.command.vm.ssh.resolve_vm_name",
            return_value="test-vm",
        ),
        patch(
            "cloudmesh.ai.command._shared.context.state.config.get_cloud_config",
            return_value={"key_path": "/tmp/test-ssh-key", "user": "ubuntu"},
        ),
        patch(
            "cloudmesh.ai.command.vm.ssh.subprocess.run",
            return_value=subprocess.CompletedProcess(
                args=["ssh"], returncode=255
            ),
        ) as mock_run,
    ):
        result = CliRunner().invoke(cmx, ["vm", "ssh", "test-vm"])

    mock_run.assert_called_once()
    assert result.exit_code != 0, (
        "SSH returned exit code 255, but the CLI reported success."
    )
    assert "SSH connection failed" in result.output


import pytest


@pytest.mark.parametrize(
    "failure",
    [
        subprocess.CalledProcessError(
            255, ["ssh", "-i", "/private/secret-key"]
        ),
        subprocess.TimeoutExpired(
            ["ssh", "-i", "/private/secret-key"], timeout=30
        ),
        RuntimeError("SSH failed using /private/secret-key"),
    ],
    ids=["called-process-error", "timeout", "generic-exception"],
)
def test_ssh_subprocess_failure_does_not_expose_key_path(failure):
    """Subprocess failures must produce safe CLI errors."""
    provider = MagicMock()
    provider.cloud_name = "test-openstack"
    provider.info.return_value = {"ip": "192.0.2.10"}

    with (
        patch(
            "cloudmesh.ai.command.vm.ssh.get_active_provider",
            return_value=provider,
        ),
        patch(
            "cloudmesh.ai.command.vm.ssh.resolve_vm_name",
            return_value="test-vm",
        ),
        patch(
            "cloudmesh.ai.command._shared.context.state.config.get_cloud_config",
            return_value={
                "key_path": "/private/secret-key",
                "user": "ubuntu",
            },
        ),
        patch(
            "cloudmesh.ai.command.vm.ssh.subprocess.run",
            side_effect=failure,
        ),
    ):
        result = CliRunner().invoke(cmx, ["vm", "ssh", "test-vm"])

    assert result.exit_code != 0
    assert "SSH connection failed" in result.output
    assert "/private/secret-key" not in result.output
