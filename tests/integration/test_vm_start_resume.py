import os
import shutil
import time
import uuid

import pytest
import yaml
from click.testing import CliRunner

from cloudmesh.ai.command.vm import cmx
from cloudmesh.ai.command._shared.context import state
from cloudmesh.ai.vm.providers import get_provider
from cloudmesh.ai.vm.state_manager import StateManager


def wait_for_status(provider, vm_name, expected_status, timeout=120):
    """Wait until a VM reaches the expected status."""
    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        for vm in provider.list() or []:
            if vm.get("name") == vm_name:
                status = str(vm.get("status", "")).lower()
                if status == expected_status.lower():
                    return True

        time.sleep(2)

    return False


def wait_for_deletion(provider, vm_name, timeout=60):
    """Wait until a VM disappears from the provider inventory."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        existing_vms = provider.list() or []
        if not any(vm.get("name") == vm_name for vm in existing_vms):
            return True
        time.sleep(2)
    return False


@pytest.mark.parametrize(
    ("provider_name", "binary_name", "provider_config"),
    [
        ("lima", "limactl", {"template": "ubuntu"}),
        ("multipass", "multipass", {"image": "22.04"}),
    ],
)
def test_cli_resumes_stopped_local_vm(
    provider_name,
    binary_name,
    provider_config,
    tmp_path,
):
    """
    Test the real CLI lifecycle:
    create -> stop -> resume -> reject duplicate start -> delete.
    """
    if os.environ.get("CLOUDMESH_RUN_LOCAL_RESUME_TESTS") != "1":
        pytest.skip(
            "Set CLOUDMESH_RUN_LOCAL_RESUME_TESTS=1 to enable "
            "real local VM lifecycle tests."
        )

    if shutil.which(binary_name) is None:
        pytest.skip(f"{binary_name} is not installed.")

    config_path = tmp_path / "clouds.yaml"

    config_data = {
        "default_cloud": provider_name,
        "clouds": {
            provider_name: {
                **provider_config,
                "username": "resume_test",
            }
        },
    }

    config_path.write_text(yaml.safe_dump(config_data))

    manager = StateManager(str(config_path))
    original_manager = state._manager
    state.set_manager(manager)

    runner = CliRunner()
    vm_name = f"resume-test-{uuid.uuid4().hex[:8]}"

    try:
        provider = get_provider(provider_name)

        # 1. Create a new VM through the actual CLI.
        result = runner.invoke(
            cmx,
            ["vm", "--cloud", provider_name, "start", vm_name],
        )
        assert result.exit_code == 0, result.output

        assert wait_for_status(provider, vm_name, "Running"), (
            f"{provider_name} VM did not reach Running status."
        )

        # 2. Stop the VM through the actual CLI.
        original_vms = [
            vm for vm in (provider.list() or [])
            if vm.get("name") == vm_name
        ]
        assert len(original_vms) == 1

        result = runner.invoke(
            cmx,
            ["vm", "--cloud", provider_name, "stop", vm_name],
        )
        assert result.exit_code == 0, result.output

        assert wait_for_status(provider, vm_name, "Stopped"), (
            f"{provider_name} VM did not reach Stopped status."
        )

        # 3. Resume the existing VM through the actual CLI.
        result = runner.invoke(
            cmx,
            ["vm", "--cloud", provider_name, "start", vm_name],
        )
        assert result.exit_code == 0, result.output

        assert wait_for_status(provider, vm_name, "Running"), (
            f"{provider_name} VM did not resume successfully."
        )

        resumed_vms = [
            vm for vm in (provider.list() or [])
            if vm.get("name") == vm_name
        ]
        assert len(resumed_vms) == 1
        assert resumed_vms[0]["name"] == original_vms[0]["name"]

        # 4. Starting an already-running VM must be rejected.
        result = runner.invoke(
            cmx,
            ["vm", "--cloud", provider_name, "start", vm_name],
        )

        assert result.exit_code != 0
        normalized_output = " ".join(result.output.split())
        assert "already exists" in normalized_output
        assert f"provider '{provider_name}'" in normalized_output

    finally:
        try:
            provider = get_provider(provider_name)
            if provider.exists(vm_name):
                provider.delete(vm_name)
            assert wait_for_deletion(provider, vm_name), (
                f"VM {vm_name} still exists after cleanup."
            )
        except Exception as exc:
            print(f"Cleanup warning for {vm_name}: {exc}")
        finally:
            state.set_manager(original_manager)
