import os
import yaml
import pytest
import shutil
import uuid
import time
from cloudmesh.ai.vm.state_manager import StateManager
from cloudmesh.ai.vm.factory import factory
from cloudmesh.ai.vm.openstack.OpenstackManager import OpenstackManager
from cloudmesh.ai.common.stopwatch import StopWatch

# Register the provider in the factory for the test
factory.register("jetstream", OpenstackManager)

@pytest.mark.skipif(
    not shutil.which("openstack"),
    reason="OpenStack CLI not found; this test requires a real environment or mocks"
)
def test_jetstream_smoke():
    """
    Smoke test for Jetstream provider:
    Start -> List -> Stop -> Delete
    """
    # Use the real configuration instead of a temporary one
    from cloudmesh.ai.command.vm._shared.context import state
    config = state.config
    try:
        provider = factory.create("jetstream", config)
    except Exception as e:
        pytest.fail(f"Jetstream provider creation failed: {e}")


    # Use unique name based on cloud user and a random suffix
    cloud_config = provider.get_cloud_config("jetstream")
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
        with StopWatch.timer("jetstream_start"):
            print(f"\nStarting VM {vm_name}...")
            try:
                provider.start(vm_name)
            except Exception as e:
                pytest.skip(f"Jetstream start failed (expected without real credentials): {e}")

        # Readiness checks
        with StopWatch.timer("jetstream_wait_active"):
            print(f"Waiting for VM {vm_name} to become active...")
            assert provider.wait_for_active(vm_name) is True, f"VM {vm_name} failed to become active"

        with StopWatch.timer("jetstream_wait_login"):
            print(f"Waiting for SSH login to be available on VM {vm_name}...")
            assert provider.wait_for_login(vm_name) is True, f"SSH login not available on VM {vm_name}"


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
        StopWatch.benchmark(tag=f"Jetstream Smoke {vm_name}")

        # Cleanup in case of failure
        try:
            if provider.exists(vm_name):
                provider.delete(vm_name)
        except Exception:
            pass
