import os
import yaml
import pytest
import uuid
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
        "username": "func_test_user",
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

def test_multipass_functionality(temp_config, ssh_key):
    """
    Functional test for Multipass provider:
    1. Launch VM
    2. Upload SSH Key
    3. Verify SSH Key
    4. Reset Daemon
    5. Cleanup
    """
    priv_key_path, pub_key_path = ssh_key
    state = StateManager(temp_config)
    provider = factory.create("multipass", state.config)

    # Unique name for the VM
    vm_name = f"func-multipass-{uuid.uuid4().hex[:6]}"

    try:
        # 1. Launch VM
        with StopWatch.timer("multipass_func_start"):
            print(f"\nLaunching VM {vm_name}...")
            provider.start(vm_name)
            assert provider.wait_for_status(vm_name, "Running", timeout=60) is True

        # 2. Upload SSH Key
        with StopWatch.timer("multipass_func_upload_key"):
            print(f"Uploading SSH key from {pub_key_path}...")
            assert provider.upload_key(pub_key_path, "test-key", vm_name) is True

        # 3. Verify the key is in the VM
        with StopWatch.timer("multipass_func_verify_key"):
            print("Verifying SSH key in VM...")
            # We use multipass exec to check authorized_keys
            # We look for the content of the public key
            with open(pub_key_path, "r") as f:
                pub_key_content = f.read().strip()

            # We escape single quotes in the key for the bash command
            escaped_key = pub_key_content.replace("'", "'\\''")
            verify_cmd = ["multipass", "exec", vm_name, "--", "bash", "-c", f"grep -q '{escaped_key}' ~/.ssh/authorized_keys"]

            result = subprocess.run(verify_cmd, capture_output=True)
            assert result.returncode == 0, f"SSH key was not found in {vm_name}'s authorized_keys"
            print("SSH key verified successfully.")

        # 4. Reset the daemon
        with StopWatch.timer("multipass_func_reset_daemon"):
            print("Resetting Multipass daemon...")
            # Note: reset() only works on macOS in the current implementation
            import platform
            if platform.system() == "Darwin":
                assert provider.reset() is True
                print("Daemon reset successfully.")

                # Verify VM is still accessible/exists after reset
                assert provider.exists(vm_name) is True
                print("VM still exists after daemon reset.")
            else:
                print("Skipping daemon reset (not on macOS).")

    finally:
        # 5. Cleanup
        with StopWatch.timer("multipass_func_cleanup"):
            print(f"Cleaning up VM {vm_name}...")
            try:
                provider.delete(vm_name)
            except Exception as e:
                print(f"Cleanup failed: {e}")

            # Verify it's gone
            vms = provider.list()
            assert not any(vm.get("name") == vm_name for vm in vms), f"VM {vm_name} should have been deleted"
            print("Cleanup complete.")

        # Print the benchmark results
        StopWatch.benchmark(tag=f"Multipass Func {vm_name}")

    print("\nMultipass functionality test passed!")
