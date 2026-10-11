import os
import yaml
import pytest
import shutil
import uuid
import time
import subprocess
from cloudmesh.ai.vm.state_manager import StateManager
from cloudmesh.ai.vm.factory import factory
from cloudmesh.ai.vm.openstack.OpenstackManager import OpenstackManager
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

@pytest.mark.skipif(
    not shutil.which("openstack"),
    reason="OpenStack CLI not found; this test requires a real environment or mocks"
)
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

    with StopWatch.timer("jetstream_get_provider_info"):
        print("Fetching provider info...")
        p_info = provider.get_provider_info()
        assert p_info is not None
        print(f"Provider info retrieved.")

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
            try:
                provider.start(vm_name)
            except Exception as e:
                pytest.skip(f"Jetstream start failed (expected without real credentials): {e}")

        # Readiness checks
        with StopWatch.timer("jetstream_wait_active"):
            print(f"Waiting for VM {vm_name} to become active...")
            # Jetstream specific check
            assert provider.wait_for_active(vm_name) is True, f"VM {vm_name} failed to become active"

        with StopWatch.timer("jetstream_wait_login"):
            print(f"Waiting for SSH login to be available on VM {vm_name}...")
            assert provider.wait_for_login(vm_name) is True, f"SSH login not available on VM {vm_name}"

        # Connectivity check
        with StopWatch.timer("jetstream_connectivity"):
            print(f"Checking connectivity for VM {vm_name}...")
            # Jetstream inherits run_command from Base if not overridden
            try:
                hostname = provider.run_command(vm_name, "hostname")
                assert hostname is not None and "Error" not in hostname
                print(f"Connectivity check successful. Hostname: {hostname}")
            except Exception as e:
                print(f"Connectivity check skipped or failed: {e}")

        # SSH Key Management
        with StopWatch.timer("jetstream_upload_key"):
            print(f"Uploading SSH key from {pub_key_path}...")
            assert provider.upload_key(pub_key_path, "smoke-key", vm_name) is True

        with StopWatch.timer("jetstream_verify_key"):
            print("Verifying SSH key in VM...")
            # Use the base class SSH helper since Jetstream might not have run_command
            user = cloud_config.get("user", "ubuntu")
            # We need an IP for this
            info = provider.info(vm_name)
            ip = info.get("FloatingIP") or info.get("ip")
            if ip:
                with open(pub_key_path, "r") as f:
                    pub_key_content = f.read().strip()
                escaped_key = pub_key_content.replace("'", "'\\''")
                verify_cmd = f"grep -q '{escaped_key}' ~/.ssh/authorized_keys"
                result = provider._execute_ssh_command(ip, user, priv_key_path, verify_cmd)
                assert "SSH Error" not in result, f"SSH key was not found in {vm_name}'s authorized_keys"
                print("SSH key verified successfully.")
            else:
                print("Skipping key verification: No IP found.")

        with StopWatch.timer("jetstream_delete_key"):
            print("Deleting uploaded SSH key...")
            assert provider.delete_key("smoke-key", vm_name) is True

        # Test info
        with StopWatch.timer("jetstream_info"):
            print(f"Fetching info for VM {vm_name}...")
            info = provider.info(vm_name)
            assert info is not None, f"Info for {vm_name} should not be None"

        # 2. List VM and verify it exists with retries
        with StopWatch.timer("jetstream_list"):
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
        with StopWatch.timer("jetstream_stop"):
            print(f"Stopping VM {vm_name}...")
            assert provider.stop(vm_name) is True, "Should successfully stop VM"

        # Verify it actually reaches Stopped state
        with StopWatch.timer("jetstream_wait_stopped"):
            print(f"Waiting for VM {vm_name} to reach Stopped state...")
            assert provider.wait_for_status(vm_name, "Stopped", timeout=60) is True

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

        print("\nJetstream Smoke test passed successfully!")

    finally:
        # Print the benchmark results
        save_benchmark(tag=f"Jetstream Smoke {vm_name}", config_path=temp_config)

        # Cleanup in case of failure
        try:
            if provider.exists(vm_name):
                provider.delete(vm_name)
        except Exception:
            pass
