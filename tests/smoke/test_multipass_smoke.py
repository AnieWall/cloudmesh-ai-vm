import os
import yaml
import pytest
import shutil
import uuid
import time
import subprocess
from cloudmesh.ai.vm.state_manager import StateManager
from cloudmesh.ai.vm.factory import factory
from cloudmesh.ai.vm.local.MultipassManager import Provider as MultipassProvider
from cloudmesh.ai.common.stopwatch import StopWatch

# Register the provider in the factory for the test
factory.register("multipass", MultipassProvider)

@pytest.fixture
def temp_config(tmp_path):
    """Create a temporary clouds.yaml for testing."""
    config_dir = tmp_path / ".config" / "cloudmesh"
    config_dir.mkdir(parents=True)
    config_file = config_dir / "clouds.yaml"

    config_data = {
        "username": "smoke_test_user",
        "clouds": {
            "multipass": {
                "image": "22.04"
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

    # Generate key without passphrase
    subprocess.run(
        ["ssh-keygen", "-t", "rsa", "-b", "2048", "-f", str(key_path), "-N", ""],
        check=True,
        capture_output=True
    )

    return str(key_path), str(pub_key_path)

def test_multipass_smoke(temp_config, ssh_key):
    """
    Smoke test for Multipass provider:
    Start -> SSH Key Upload -> Verify Key -> List -> Stop -> Delete
    """
    priv_key_path, pub_key_path = ssh_key
    state = StateManager(temp_config)
    provider = factory.create("multipass", state.config)

    # Use unique name based on cloud user and a random suffix
    cloud_config = provider.get_cloud_config("multipass")
    username = cloud_config.get("username", "user").replace("_", "-")
    vm_name = f"smoke-{username}-{uuid.uuid4().hex[:6]}"

    try:
        # 0. Cleanup any existing VM with the same name (rare with UUID, but safe)
        print(f"Cleaning up existing VM {vm_name} if it exists...")
        try:
            provider.delete(vm_name)
        except Exception:
            pass

        # 1. Start VM
        with StopWatch.timer("multipass_start"):
            print(f"\nStarting VM {vm_name}...")
            provider.start(vm_name)

        # Verify it actually reaches Running state
        with StopWatch.timer("multipass_wait_running"):
            print(f"Waiting for VM {vm_name} to reach Running state...")
            assert provider.wait_for_status(vm_name, "Running", timeout=60) is True

        # Connectivity check
        with StopWatch.timer("multipass_connectivity"):
            print(f"Checking connectivity for VM {vm_name}...")
            hostname = provider.run_command(vm_name, "hostname")
            assert hostname is not None and hostname != "" and "Error" not in hostname, \
                f"Connectivity check failed for {vm_name}: {hostname}"
            print(f"Connectivity check successful. Hostname: {hostname}")

        # SSH Key Upload
        with StopWatch.timer("multipass_upload_key"):
            print(f"Uploading SSH key from {pub_key_path}...")
            assert provider.upload_key(pub_key_path, "smoke-key", vm_name) is True

        # Verify SSH Key
        with StopWatch.timer("multipass_verify_key"):
            print("Verifying SSH key in VM...")
            with open(pub_key_path, "r") as f:
                pub_key_content = f.read().strip()

            escaped_key = pub_key_content.replace("'", "'\\''")
            verify_cmd = ["multipass", "exec", vm_name, "--", "bash", "-c", f"grep -q '{escaped_key}' ~/.ssh/authorized_keys"]

            result = subprocess.run(verify_cmd, capture_output=True)
            assert result.returncode == 0, f"SSH key was not found in {vm_name}'s authorized_keys"
            print("SSH key verified successfully.")

        # Test info
        with StopWatch.timer("multipass_info"):
            print(f"Fetching info for VM {vm_name}...")
            info = provider.info(vm_name)
            assert info is not None, f"Info for {vm_name} should not be None"

        # 2. List VM and verify it exists with retries
        with StopWatch.timer("multipass_list"):
            print("Verifying VM in list...")
            vm_exists = False
            for i in range(5):
                vms = provider.list()
                if any(vm.get("name") == vm_name for vm in vms):
                    vm_exists = True
                    break
                print(f"VM not found yet, retrying {i+1}/5...")
                time.sleep(2)
            assert vm_exists, f"VM {vm_name} should exist in the list"

        # 3. Stop VM
        with StopWatch.timer("multipass_stop"):
            print(f"Stopping VM {vm_name}...")
            assert provider.stop(vm_name) is True, "Should successfully stop VM"

        # Verify it actually reaches Stopped state
        with StopWatch.timer("multipass_wait_stopped"):
            print(f"Waiting for VM {vm_name} to reach Stopped state...")
            assert provider.wait_for_status(vm_name, "Stopped", timeout=60) is True

        # 4. Delete VM
        with StopWatch.timer("multipass_delete"):
            print(f"Deleting VM {vm_name}...")
            assert provider.delete(vm_name) is True, "Should successfully delete VM"

        # 5. Verify VM is gone
        with StopWatch.timer("multipass_verify_deleted"):
            print("Verifying VM is deleted...")
            vms = provider.list()
            vm_exists = any(vm.get("name") == vm_name for vm in vms)
            assert not vm_exists, f"VM {vm_name} should be gone from the list"

        print("\nSmoke test passed successfully!")

    finally:
        # Print the benchmark results
        StopWatch.benchmark(tag=f"Multipass Smoke {vm_name}")

        # Cleanup in case of failure
        try:
            if provider.exists(vm_name):
                provider.delete(vm_name)
        except Exception:
            pass
