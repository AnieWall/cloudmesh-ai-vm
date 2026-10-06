import os
import yaml
import pytest
import uuid
import time
from cloudmesh.ai.vm.state_manager import StateManager
from cloudmesh.ai.vm.factory import factory
from cloudmesh.ai.vm.local.VBoxManager import Provider as VBoxProvider
from cloudmesh.ai.common.stopwatch import StopWatch

# Register the provider in the factory for the test
factory.register("vbox", VBoxProvider)

@pytest.fixture
def temp_config(tmp_path):
    """Create a temporary clouds.yaml for testing."""
    config_dir = tmp_path / ".config" / "cloudmesh"
    config_dir.mkdir(parents=True)
    config_file = config_dir / "clouds.yaml"

    config_data = {
        "username": "smoke_test_user",
        "clouds": {
            "vbox": {
                "image": "ubuntu-22.04"
            }
        }
    }

    with open(config_file, "w") as f:
        yaml.dump(config_data, f)

    return str(config_file)

def test_vbox_smoke(temp_config):
    """
    Smoke test for VBox provider:
    Start -> List -> Stop -> Delete
    """
    state = StateManager(temp_config)
    provider = factory.create("vbox", state.config)

    cloud_config = provider.get_cloud_config("vbox")
    username = cloud_config.get("username", "user").replace("_", "-")
    vm_name = f"smoke-vbox-{username}-{uuid.uuid4().hex[:6]}"

    try:
        # 0. Cleanup
        try:
            provider.delete(vm_name)
        except Exception:
            pass

        # 1. Start VM
        with StopWatch.timer("vbox_start"):
            print(f"\nStarting VBox VM {vm_name}...")
            provider.start(vm_name)

        with StopWatch.timer("vbox_wait_running"):
            print(f"Waiting for VBox VM {vm_name} to reach Running state...")
            assert provider.wait_for_status(vm_name, "Running", timeout=60) is True

        # 2. List VM
        with StopWatch.timer("vbox_list"):
            print("Verifying VBox VM in list...")
            vm_exists = False
            for i in range(5):
                vms = provider.list()
                if any(vm.get("name") == vm_name for vm in vms):
                    vm_exists = True
                    break
                time.sleep(2)
            assert vm_exists, f"VBox VM {vm_name} should exist"

        # 3. Stop VM
        with StopWatch.timer("vbox_stop"):
            print(f"Stopping VBox VM {vm_name}...")
            assert provider.stop(vm_name) is True

        with StopWatch.timer("vbox_wait_stopped"):
            assert provider.wait_for_status(vm_name, "Stopped", timeout=60) is True

        # 4. Delete VM
        with StopWatch.timer("vbox_delete"):
            print(f"Deleting VBox VM {vm_name}...")
            assert provider.delete(vm_name) is True

        # 5. Verify gone
        with StopWatch.timer("vbox_verify_deleted"):
            vms = provider.list()
            assert not any(vm.get("name") == vm_name for vm in vms)

        print("\nVBox Smoke test passed successfully!")

    finally:
        StopWatch.benchmark(tag=f"VBox Smoke {vm_name}")
        try:
            if provider.exists(vm_name):
                provider.delete(vm_name)
        except Exception:
            pass
