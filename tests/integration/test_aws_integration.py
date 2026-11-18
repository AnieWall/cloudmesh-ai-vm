def test_aws_lifecycle(aws_live_provider):
    """
    Run the AWS Start -> Info -> Stop -> Delete lifecycle.

    Requires CLOUDMESH_AWS_LIVE_TEST=1 and an explicitly configured
    CLOUDMESH_VM_CONFIG file containing AWS credentials and VM settings.
    """
    provider = aws_live_provider

    vm_name = "integration-test-aws-vm"

    try:
        # 1. Start VM
        print(f"Launching AWS VM {vm_name}...")
        vm_id = provider.start(name=vm_name)
        assert vm_id is not None

        # 2. Verify Info
        print(f"Fetching info for {vm_name}...")
        info = provider.info(vm_id)
        assert info["Name"] == vm_name

        # 3. Stop VM
        print(f"Stopping AWS VM {vm_name}...")
        assert provider.stop(vm_id) is True

        # 4. Delete VM
        print(f"Deleting AWS VM {vm_name}...")
        assert provider.delete(vm_id) is True

    finally:
        # Final cleanup attempt
        try:
            provider.delete(vm_name)
        except Exception:
            pass
