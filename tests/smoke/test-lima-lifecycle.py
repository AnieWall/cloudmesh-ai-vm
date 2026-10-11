import os
import yaml
import pytest
import uuid
import time
import subprocess
from cloudmesh.ai.vm.state_manager import StateManager
from cloudmesh.ai.vm.factory import factory
from cloudmesh.ai.vm.local.LimaManager import Provider as LimaProvider
from cloudmesh.ai.common.stopwatch import StopWatch
from tests.smoke.benchmark_helper import save_benchmark

# Register the provider in the factory for the test
factory.register("lima", LimaProvider)

@pytest.fixture
def temp_config(tmp_path):
    """Create a temporary clouds.yaml for testing."""
    config_dir = tmp_path / ".config" / "cloudmesh"
    config_dir.mkdir(parents=True)
    config_file = config_dir / "clouds.yaml"

    config_data = {
        "username": "smoke_test_user",
        "clouds": {
            "lima": {
                "image": "ubuntu-22.04"
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

def test_lima_smoke(temp_config, ssh_key):
    """
    Smoke test for Lima provider:
    Requirements -> Images -> Flavors -> Info -> Start -> Connectivity -> SSH Key Upload -> Verify Key -> Delete Key -> Verify Key Deleted -> Info -> List -> Stop -> Delete
    """
    priv_key_path, pub_key_path = ssh_key
    state = StateManager(temp_config)
    provider = factory.create("lima", state.config)

    # --- Provider Level Checks ---
    if hasattr(provider, "check_requirements"):
        with StopWatch.timer("lima_check_reqs"):
            print("Checking Lima requirements...")
            assert provider.check_requirements() is True

    with StopWatch.timer("lima_get_images"):
        print("Fetching available images...")
        images = provider.get_images()
        assert isinstance(images, list)
        print(f"Found {len(images)} images.")

    with StopWatch.timer("lima_get_flavors"):
        print("Fetching available flavors...")
        flavors = provider.get_flavors()
        assert isinstance(flavors, list)
        assert len(flavors) > 0
        print(f"Found {len(flavors)} flavors.")

    with StopWatch.timer("lima_get_provider_info"):
        print("Fetching provider info...")
        p_info = provider.get_provider_info()
        assert p_info is not None
        print(f"Provider info retrieved.")

    cloud_config = provider.get_cloud_config("lima")
    username = cloud_config.get("username", "user").replace("_", "-")
    vm_name = f"smoke-lima-{username}-{uuid.uuid4().hex[:6]}"

    try:
        # 0. Cleanup
        try:
            provider.delete(vm_name)
        except Exception:
            pass

        # 1. Start VM
        with StopWatch.timer("lima_start"):
            print(f"\nStarting Lima VM {vm_name}...")
            provider.start(vm_name)

        with StopWatch.timer("lima_wait_running"):
            print(f"Waiting for Lima VM {vm_name} to reach Running state...")
            assert provider.wait_for_status(vm_name, "Running", timeout=60) is True

        # Connectivity check
        with StopWatch.timer("lima_connectivity"):
            print(f"Checking connectivity for Lima VM {vm_name}...")
            hostname = provider.run_command(vm_name, "hostname")
            assert hostname is not None and hostname != "" and "Error" not in hostname, \
                f"Connectivity check failed for {vm_name}: {hostname}"
            print(f"Connectivity check successful. Hostname: {hostname}")

        # SSH Key Upload
        with StopWatch.timer("lima_upload_key"):
            print(f"Uploading SSH key from {pub_key_path}...")
            assert provider.upload_key(pub_key_path, "smoke-key", vm_name) is True

        # Verify SSH Key
        with StopWatch.timer("lima_verify_key"):
            print("Verifying SSH key in Lima VM...")
            with open(pub_key_path, "r") as f:
                pub_key_content = f.read().strip()

            escaped_key = pub_key_content.replace("'", "'\\''")
            # Use the base class helper for consistency
            user = cloud_config.get("user", "ubuntu")
            # Lima uses a local IP or special hostname
            info = provider.info(vm_name)
            ip = info.get("ip") or "lima-vm"

            verify_cmd = f"grep -q '{escaped_key}' ~/.ssh/authorized_keys"
            result = provider._execute_ssh_command(ip, user, priv_key_path, verify_cmd)
            assert "SSH Error" not in result, f"SSH key was not found in {vm_name}'s authorized_keys"
            print("SSH key verified successfully.")

        # Delete SSH Key
        with StopWatch.timer("lima_delete_key"):
            print("Deleting uploaded SSH key...")
            assert provider.delete_key("smoke-key", vm_name) is True

        # Verify SSH Key Deleted
        with StopWatch.timer("lima_verify_key_deleted"):
            print("Verifying SSH key is removed...")
            verify_cmd_del = f"grep -q '{escaped_key}' ~/.ssh/authorized_keys"
            result_del = provider._execute_ssh_command(ip, user, priv_key_path, verify_cmd_del)
            assert "SSH Error" in result_del, \
                f"SSH key should have been removed from {vm_name}"
            print("SSH key removal verified.")

        # Test info
        with StopWatch.timer("lima_info"):
            print(f"Fetching info for Lima VM {vm_name}...")
            info = provider.info(vm_name)
            assert info is not None, f"Info for {vm_name} should not be None"

        # 2. List VM
        with StopWatch.timer("lima_list"):
            print("Verifying Lima VM in list...")
            vm_exists = False
            for i in range(5):
                vms = provider.list()
                if any(vm.get("name") == vm_name for vm in vms):
                    vm_exists = True
                    break
                time.sleep(2)
            assert vm_exists, f"Lima VM {vm_name} should exist"

        # 3. Stop VM
        with StopWatch.timer("lima_stop"):
            print(f"Stopping Lima VM {vm_name}...")
            assert provider.stop(vm_name) is True

        with StopWatch.timer("lima_wait_stopped"):
            print(f"Waiting for Lima VM {vm_name} to reach Stopped state...")
            assert provider.wait_for_status(vm_name, "Stopped", timeout=60) is True

        # 4. Delete VM
        with StopWatch.timer("lima_delete"):
            print(f"Deleting Lima VM {vm_name}...")
            assert provider.delete(vm_name) is True

        # 5. Verify gone
        with StopWatch.timer("lima_verify_deleted"):
            print("Verifying Lima VM is deleted...")
            vms = provider.list()
            assert not any(vm.get("name") == vm_name for vm in vms)

        print("\nLima Smoke test passed successfully!")

    finally:
        StopWatch.benchmark(tag=f"Lima Smoke {vm_name}")
        save_benchmark(tag=f"Lima Smoke {vm_name}", config_path=temp_config)
        try:
            if provider.exists(vm_name):
                provider.delete(vm_name)
        except Exception:
            pass
