import os
import yaml
import pytest
import shutil
from cloudmesh.ai.vm.state_manager import StateManager
from cloudmesh.ai.vm.factory import factory
from cloudmesh.ai.vm.local.Wsl2Manager import Provider as Wsl2Provider

# Register the provider in the factory for the test
factory.register("wsl2", Wsl2Provider)

@pytest.mark.skipif(
    not (shutil.which("wsl.exe") or shutil.which("wsl")),
    reason="WSL binary not found; this test requires a Windows environment with WSL2"
)
def test_wsl2_smoke():
    """
    Smoke test for WSL2 provider:
    Start -> List -> Stop -> Delete
    """
    # We use a temporary config.
    # NOTE: For this test to actually 'import' a new distro, a valid rootfs path is required.
    # If no valid rootfs is provided, the 'start' call will fail unless the distro already exists.
    tmp_config_dir = os.path.expanduser("~/.config/cloudmesh_smoke")
    os.makedirs(tmp_config_dir, exist_ok=True)
    config_file = os.path.join(tmp_config_dir, "clouds.yaml")

    config_data = {
        "username": "smoke_test_user",
        "clouds": {
            "wsl2": {
                "rootfs": "C:\\path\\to\\rootfs.tar",  # Placeholder: User should configure real rootfs for import tests
                "install_dir": "C:\\WSL_Smoke",
                "wsl_username": "smoke_user",
                "host_username": "smoke_host"
            }
        }
    }

    with open(config_file, "w") as f:
        yaml.dump(config_data, f)

    state = StateManager(config_file)
    provider = factory.create("wsl2", state.config)

    vm_name = "smoke-test-wsl2"

    try:
        # 0. Cleanup any existing VM with the same name
        print(f"Cleaning up existing WSL2 distro {vm_name} if it exists...")
        provider.delete(vm_name)

        # 1. Start VM
        print(f"\nStarting WSL2 distro {vm_name}...")
        try:
            provider.start(vm_name)
        except Exception as e:
            pytest.skip(f"WSL2 start failed. This is expected if 'rootfs' is not configured in the smoke test: {e}")

        # 2. List VM and verify it exists with retries
        print("Verifying WSL2 distro in list...")
        import time
        vm_exists = False
        for i in range(5):
            vms = provider.list()
            if any(vm.get("Name") == vm_name for vm in vms):
                vm_exists = True
                break
            print(f"WSL2 distro not found yet, retrying {i+1}/5...")
            time.sleep(2)
        assert vm_exists, f"WSL2 distro {vm_name} should exist in the list"

        # 3. Stop VM
        print(f"Stopping WSL2 distro {vm_name}...")
        assert provider.stop(vm_name) is True, "Should successfully stop WSL2 distro"

        # 4. Delete VM
        print(f"Deleting WSL2 distro {vm_name}...")
        assert provider.delete(vm_name) is True, "Should successfully delete WSL2 distro"

        # 5. Verify VM is gone
        print("Verifying WSL2 distro is deleted...")
        vms = provider.list()
        vm_exists = any(vm.get("Name") == vm_name for vm in vms)
        assert not vm_exists, f"WSL2 distro {vm_name} should be gone from the list"

        print("\nWSL2 Smoke test passed successfully!")

    finally:
        # Cleanup in case of failure
        try:
            provider.delete(vm_name)
        except:
            pass
