"""Additional unit tests for the Multipass provider.

These tests cover functionality that was added or enhanced in issue #114:

* ``resume`` – counterpart to ``suspend``.
* Snapshot management – ``snapshot``, ``restore_snapshot`` and ``list_snapshots``.
* Cross‑platform ``reset`` – Linux fallback using ``systemctl``.
* Type hint cleanup – not directly exercised but ensures the methods exist.

The tests use ``unittest.mock`` to replace the heavy ``_run_command`` method with
light‑weight mocks, avoiding any real multipass calls.  Errors such as a missing
VM raise ``VMResourceError`` as defined in the project.
"""

import pytest
import shlex
from unittest.mock import MagicMock, patch

from cloudmesh.ai.vm.local.MultipassManager import Provider
from cloudmesh.ai.vm.exceptions import VMResourceError


@pytest.fixture
def mock_config():
    """Minimal configuration used by the provider fixture."""
    return {
        "clouds": {
            "multipass": {
                "image": "22.04",
                "cpus": 2,
                "memory": "4GiB",
                "disk": "20GiB",
            }
        }
    }


@pytest.fixture
def provider(mock_config):
    """Create a provider instance with a mocked ``_run_command`` method."""
    p = Provider(mock_config)
    p._run_command = MagicMock()
    return p


# ---------------------------------------------------------------------------
# Resume tests (mirror of the existing suspend tests)
# ---------------------------------------------------------------------------

def test_resume_success(provider):
    provider.exists = MagicMock(return_value=True)
    provider._run_command.return_value = MagicMock(stdout="Started", returncode=0)

    assert provider.resume(name="test-vm") is True
    provider._run_command.assert_called_with(["multipass", "start", "test-vm"])


def test_resume_missing_vm(provider):
    provider.exists = MagicMock(return_value=False)
    with pytest.raises(VMResourceError):
        provider.resume(name="nonexistent")


def test_resume_default_resolution(provider):
    provider._get_default_vm = MagicMock(return_value="default-vm")
    provider.exists = MagicMock(return_value=True)
    provider._run_command.return_value = MagicMock(stdout="Started", returncode=0)

    assert provider.resume() is True
    provider._run_command.assert_called_with(["multipass", "start", "default-vm"])


# ---------------------------------------------------------------------------
# Snapshot management tests
# ---------------------------------------------------------------------------

def test_snapshot_success(provider):
    provider.exists = MagicMock(return_value=True)
    provider._run_command.return_value = MagicMock(stdout="Snapshot created", returncode=0)

    assert provider.snapshot(name="test-vm", snapshot_name="snap1") is True
    provider._run_command.assert_called_with(["multipass", "snapshot", "test-vm", "snap1"])


def test_snapshot_missing_vm(provider):
    provider.exists = MagicMock(return_value=False)
    with pytest.raises(VMResourceError):
        provider.snapshot(name="missing", snapshot_name="snap1")


def test_snapshot_missing_name(provider):
    provider.exists = MagicMock(return_value=True)
    with pytest.raises(ValueError):
        provider.snapshot(name="test-vm")


def test_restore_snapshot_success(provider):
    provider.exists = MagicMock(return_value=True)
    provider._run_command.return_value = MagicMock(stdout="Restored", returncode=0)

    assert provider.restore_snapshot(name="test-vm", snapshot_name="snap1") is True
    provider._run_command.assert_called_with(["multipass", "restore", "test-vm", "snap1"])


def test_restore_snapshot_missing_name(provider):
    provider.exists = MagicMock(return_value=True)
    with pytest.raises(ValueError):
        provider.restore_snapshot(name="test-vm")


def test_list_snapshots_json(provider):
    # Simulate ``info`` returning a JSON‑compatible dict with snapshots.
    provider.info = MagicMock(return_value={"snapshots": {"snap1": {"created": "2023"}, "snap2": {}}})
    provider.exists = MagicMock(return_value=True)
    result = provider.list_snapshots(name="test-vm")
    # Expect a list of two entries where each contains at least the name.
    assert isinstance(result, list)
    assert {entry["name"] for entry in result} == {"snap1", "snap2"}
    # ``snap1`` entry should contain the ``created`` field.
    snap1 = next(e for e in result if e["name"] == "snap1")
    assert snap1.get("created") == "2023"


def test_list_snapshots_fallback(provider):
    # ``info`` without snapshots triggers the CLI fallback.
    provider.info = MagicMock(return_value={})
    provider.exists = MagicMock(return_value=True)
    fake_stdout = (
        "Name        Created\n"
        "snap1       2023-01-01T00:00:00Z\n"
        "snap2       2023-01-02T00:00:00Z\n"
    )
    provider._run_command.return_value = MagicMock(stdout=fake_stdout, returncode=0)

    result = provider.list_snapshots(name="test-vm")
    assert isinstance(result, list)
    names = [snap["name"] for snap in result]
    assert "snap1" in names and "snap2" in names
    # Details should be captured in the ``details`` key.
    details = {snap["name"]: snap.get("details") for snap in result}
    assert details["snap1"].strip() == "2023-01-01T00:00:00Z"


# ---------------------------------------------------------------------------
# Reset – Linux fallback
# ---------------------------------------------------------------------------

def test_reset_linux_success(provider):
    # Force the platform to be Linux.
    with patch("platform.system", return_value="Linux"):
        provider._run_command.return_value = MagicMock()
        assert provider.reset() is True
        provider._run_command.assert_called_once_with([
            "systemctl",
            "restart",
            "snap.multipass.multipassd.service",
        ])


def test_reset_linux_failure(provider):
    with patch("platform.system", return_value="Linux"):
        provider._run_command.side_effect = Exception("systemctl failed")
        assert provider.reset() is False
        provider._run_command.assert_called_once()
