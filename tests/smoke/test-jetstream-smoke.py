import os
import yaml
import pytest
import uuid
import time
import subprocess
from cloudmesh.ai.vm.state_manager import StateManager
from cloudmesh.ai.vm.factory import factory
from src.cloudmesh.ai.vm.openstack.OpenstackManager import OpenstackManager
from cloudmesh.ai.common.stopwatch import StopWatch
from tests.smoke.benchmark_helper import save_benchmark

# Register the provider in the factory for the test
factory.register("jetstream", OpenstackManager)

@pytest.fixture
def temp_config(tmp_path):
    """Create a temporary clouds.yaml for testing."""
    config_dir = tmp_path / ".config" / "cloudmesh"
    config_dir.mkdir(parents=True)
    config_file = config_dir / "clouds.yaml"

    config_data = {
        "username": "smoke_test_user",
        "clouds": {
            "jetstream": {
                "image": "ubuntu-22.04",
                "flavor": "m1.small",
            }
        }
    }

    with open(config_file, "w") as f:
        yaml.dump(config_data, f)

    return str(config_file)

@pytest.fixture
def ssh_key(tmp_path):
    """Generate a temporary SSH key pair."""
    key_path = tmp_path / "id_rsa"
    pub_key_path = tmp_path / "id_rsa.pub"

    subprocess.run(
        ["ssh-keygen", "-t", "rsa", "-b", "2048", "-f", str(key_path), "-N", ""],
        check=True,
        capture_output=True
    )

    return str(key_path), str(pub_key_path)

def test_jetstream_smoke(temp_config, ssh_key):
    """
    Smoke test for Jetstream provider:
    Requirements -> Images -> Flavors -> Info -> Start -> Key Mgmt -> List -> Stop -> Delete
    """
    priv_key_path, pub_key_path = ssh_key
    state = StateManager(temp_config)
    provider = factory.create("jetstream", state.config)

    # --- Provider Level Checks ---
    if hasattr(provider, "check_requirements"):
        with StopWatch.timer("jetstream_check_reqs"):
            print("Checking Jetstream requirements...")
            assert provider.check_requirements() is True

    with StopWatch.timer("jetstream_get_images"):
        print("Fetching available images...")
        images = provider.get_images()
        assert isinstance(images, list)
        print(f"Found {len(images)} images.")

    with StopWatch.timer("jetstream_get_flavors"):
        print("Fetching available flavors...")
        flavors = provider.get_flavors()
        assert isinstance(flavors, list)
        assert len(flavors) > 0
        print(f"Found {len(flavors)} flavors.")

    # Use unique name based on cloud user and a random suffix
    cloud_config = provider.get_cloud_config("jetstream")
    username = cloud_config.get("username", "user").replace("_", "-")
    vm_name = f"smoke-{username}-{uuid.uuid4().hex[:6]}"

    try:
        # 0. Cleanup any existing VM with the same name
        print(f"Cleaning up existing VM {vm_name} if it exists...")
        try:
            provider.delete(vm_name)
        except Exception:
            pass

        # 1. Start VM
        with StopWatch.timer("jetstream_start"):
            print(f"\nStarting VM {vm_name}...")
            server_id = provider.start(name=vm_name)
            assert server_id is not None

        # Verify it actually reaches Running state
        with StopWatch.timer("jetstream_wait_running"):
            print(f"Waiting for VM {vm_name} to reach Running state...")
            assert provider.wait_for_status(vm_name, "active", timeout=600) is True

        # Connectivity check
        with StopWatch.timer("jetstream_assign_fip"):
            print(f"Assigning floating IP for VM {vm_name}...")
            fip = provider.assign_floating_ip(vm_name)
            assert fip is not None
            print(f"Floating IP associated: {fip}")

        with StopWatch.timer("jetstream_connectivity"):
            print(f"Checking connectivity for VM {vm_name}...")
            user = cloud_config.get("user", "ubuntu")
            hostname = provider._execute_ssh_command(fip, user, priv_key_path, "hostname")
            assert "Error" not in hostname, f"Connectivity check failed for {vm_name}: {hostname}"
            print(f"Connectivity check successful. Hostname: {hostname}")

        # SSH Key Management
        with StopWatch.timer("jetstream_upload_key"):
            print(f"Uploading SSH key from {pub_key_path}...")
            assert provider.upload_key(pub_key_path, "smoke-key", vm_name) is True

        with StopWatch.timer("jetstream_verify_key"):
            print("Verifying SSH key in VM...")
            with open(pub_key_path, "r") as f:
                pub_key_content = f.read().strip()

            escaped_key = pub_key_content.replace("'", "'\''")
            verify_cmd = f"grep -q '{escaped_key}' ~/.ssh/authorized_keys"
            result = provider._execute_ssh_command(fip, user, priv_key_path, verify_cmd)
            assert "SSH Error" not in result, f"SSH key was not found in {vm_name}'s authorized_keys"
            print("SSH key verified successfully.")

        with StopWatch.timer("jetstream_delete_key"):
            print("Deleting uploaded SSH key...")
            assert provider.delete_key("smoke-key", vm_name) is True

        with StopWatch.timer("jetstream_verify_key_deleted"):
            print("Verifying SSH key is removed...")
            verify_cmd_del = f"grep -q '{escaped_key}' ~/.ssh/authorized_keys"
            result_del = provider._execute_ssh_command(fip, user, priv_key_path, verify_cmd_del)
            assert "SSH Error" in result_del, f"SSH key should have been removed from {vm_name}"
            print("SSH key removal verified.")

        # Test info
        with StopWatch.timer("jetstream_info"):
            print(f"Fetching info for VM {vm_name}...")
            info = provider.info(vm_name)
            assert info is not None, f"Info for {vm_name} should not be None"

        # 2. List VM and verify it exists
        with StopWatch.timer("jetstream_list"):
            print("Verifying VM in list...")
            vms = provider.list()
            vm_exists = any(vm.get("name") == vm_name for vm in vms)
            assert vm_exists, f"VM {vm_name} should exist in the list"

        # 3. Stop VM
        with StopWatch.timer("jetstream_stop"):
            print(f"Stopping VM {vm_name}...")
            assert provider.stop(vm_name) is True, "Should successfully stop VM"

        # Verify it actually reaches Stopped state
        with StopWatch.timer("jetstream_wait_stopped"):
            print(f"Waiting for VM {vm_name} to reach Stopped state...")
            assert provider.wait_for_status(vm_name, "stopped", timeout=600) is True

        # 4. Delete VM
        with StopWatch.timer("jetstream_delete"):
            print(f"Deleting VM {vm_name}...")
            assert provider.delete(vm_name) is True, "Should successfully delete VM"

        # 5. Verify VM is gone
        with StopWatch.timer("jetstream_verify_deleted"):
            print("Verifying VM is deleted...")
            vms = provider.list()
            vm_exists = any(vm.get("name") == vm_name for vm in vms)
            assert not vm_exists, f"VM {vm_name} should be gone from the list"

        print("\nSmoke test passed successfully!")

    finally:
        save_benchmark(tag="jetstream-smoke", config_path=temp_config)

        # Cleanup in case of failure
        try:
            if provider.exists(vm_name):
                provider.delete(vm_name)
        except Exception:
            pass
