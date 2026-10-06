import pytest
import uuid
from cloudmesh.ai.vm.factory import factory
from cloudmesh.ai.vm.state_manager import StateManager
from cloudmesh.ai.common.stopwatch import StopWatch

def run_lifecycle_test(provider, cloud_name, vm_name):
    """Helper to run the lifecycle test logic."""
    try:
        # 1. Start VM
        with StopWatch.timer(f"{cloud_name}_start"):
            print(f"\nLaunching {cloud_name} VM {vm_name}...")
            vm_id = provider.start(name=vm_name)
            assert vm_id is not None

        # 2. Verify Info
        with StopWatch.timer(f"{cloud_name}_info"):
            print(f"Fetching info for {vm_name}...")
            info = provider.info(vm_id)
            assert info is not None
            assert info.get("Name") == vm_name or info.get("name") == vm_name

        # 3. Stop VM
        with StopWatch.timer(f"{cloud_name}_stop"):
            print(f"Stopping {cloud_name} VM {vm_name}...")
            assert provider.stop(vm_id) is True

        # 4. Delete VM
        with StopWatch.timer(f"{cloud_name}_delete"):
            print(f"Deleting {cloud_name} VM {vm_name}...")
            assert provider.delete(vm_id) is True

    finally:
        # Final cleanup attempt
        try:
            provider.delete(vm_name)
        except Exception:
            pass

        StopWatch.benchmark(tag=f"{cloud_name} Integration {vm_name}")

@pytest.mark.parametrize("cloud_name", ["aws", "azure", "google", "lima", "vbox", "wsl2"])
def test_provider_integration(get_provider, cloud_name):
    """
    Integration test for various VM providers.
    Full lifecycle test: Start -> Info -> Stop -> Delete.
    """
    try:
        provider = get_provider(cloud_name)
    except Exception as e:
        pytest.skip(f"Credentials for {cloud_name} not configured or provider error: {e}")

    vm_name = f"int-test-{cloud_name}-{uuid.uuid4().hex[:6]}"
    run_lifecycle_test(provider, cloud_name, vm_name)
