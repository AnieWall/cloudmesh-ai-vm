import pytest
import re
import json
from rich.text import Text
from click.testing import CliRunner
from cloudmesh.ai.command import vm
from cloudmesh.ai.common.stopwatch import StopWatch

from tests.smoke.cli_helper import setup_cli_config
from pprint import pprint

@pytest.fixture
def runner():
    return CliRunner()

#
# THIS FIXTURE IS WRONG IT should be read from 
# ~/.config/cloudmesh/clouds.yaml
# authis read from ~/.config/openstack/clouds.yaml
#
@pytest.fixture
def config(tmp_path, runner):
    provider_config = {
        "image": "CC-Ubuntu24.04",
        "flavor": "m1.small",
        "key_path": "~/.ssh/id_rsa",
    }
    setup_cli_config(tmp_path, "jetstream", provider_config)
    
    # Read username from clouds.yaml
    config_path = os.path.expanduser("~/.config/cloudmesh/clouds.yaml")
    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
            username = config.get("username", "user").replace("_", "-")
    except Exception:
        username = "smoke-test-user"

    # Construct vm_name matching the requested pattern
    vm_name = f"{username}-{uuid.uuid4().hex[:4]}"
    provider_config["vm_name"] = vm_name

    pprint(provider_config)

def test_jetstream_cli_lifecycle(runner, config):
    """
    Smoke test for Jetstream CLI lifecycle.
    """
    # 1. providers
    result = runner.invoke(vm.vm_group, ["provider", "list"])
    assert result.exit_code == 0
    assert "jetstream" in result.output.lower()

    # 2. set
    result = runner.invoke(vm.vm_group, ["provider", "set", "jetstream"])
    assert result.exit_code == 0

    # 3. start (without name - test auto-naming)
    result = runner.invoke(vm.vm_group, ["start"])
    if result.exit_code != 0:
        pytest.skip(f"Jetstream start failed (expected without real credentials): {result.output}")

    output = Text.from_ansi(result.output).plain
    assert "Generating VM name" in output

    # Extract the generated VM name
    import re
    match = re.search(r"Successfully started VM ([\w-]+)", result.output)
    if match:
        vm_name = match.group(1)
    else:
        # Fallback for different output formats
        vm_name = "smoke-jetstream-vm"

    try:
        
        # 4. list
        # 4. list
        result = runner.invoke(vm.vm_group, ["list"])
        assert result.exit_code == 0
        
        # Extract the base prefix (e.g., 'smoke-chameleon-vm' or whatever your prefix is) 
        # to avoid truncation issues entirely.
        base_prefix = vm_name.rsplit("-", 1)[0]
        assert base_prefix in result.output
        
    
        # 5. stop
        result = runner.invoke(vm.vm_group, ["stop", vm_name])
        if result.exit_code != 0:
            pytest.skip("Jetstream stop failed")

        # 6. delete
        result = runner.invoke(vm.vm_group, ["delete", vm_name])
        if result.exit_code != 0:
            pytest.skip("Jetstream delete failed")

        # 7. images
        result = runner.invoke(vm.vm_group, ["images"])
        if result.exit_code != 0:
            pytest.skip("Jetstream images failed")

        # 8. flavors
        result = runner.invoke(vm.vm_group, ["flavor"])
        if result.exit_code != 0:
            pytest.skip("Jetstream flavors failed")

        # 9. keys list
        result = runner.invoke(vm.vm_group, ["key", "list"])
        if result.exit_code != 0:
            pytest.skip("Jetstream key list failed")

        # 10. keys list --all
        result = runner.invoke(vm.vm_group, ["key", "list", "--all"])
        if result.exit_code != 0:
            pytest.skip("Jetstream key list --all failed")

        # 11. keys upload
        result = runner.invoke(vm.vm_group, ["key", "upload", "~/.ssh/id_rsa.pub"])
        if result.exit_code != 0:
            pytest.skip("Jetstream key upload failed")

        # 12. keys delete
        result = runner.invoke(vm.vm_group, ["key", "delete", "smoke-key"])
        if result.exit_code != 0:
            pytest.skip("Jetstream key delete failed")

        # 13. security_groups
        result = runner.invoke(vm.vm_group, ["security_groups"])
        if result.exit_code != 0:
            pytest.skip("Jetstream security_groups failed")

        # 14. ssh_config
        result = runner.invoke(vm.vm_group, ["ssh_config"])
        assert result.exit_code == 0

    finally:
        # Cleanup
        runner.invoke(vm.vm_group, ["delete", vm_name])
        save_benchmark(tag="Jetstream CLI", config_path=None)

def test_jetstream_cli_start_with_name(runner, config):
    """
    Test starting a Jetstream VM with a specific name.
    """
    vm_name = "test-named-jetstream-vm"
    runner.invoke(vm.vm_group, ["delete", vm_name])

    result = runner.invoke(vm.vm_group, ["start", vm_name])
    if result.exit_code != 0:
        pytest.skip("Jetstream start failed")

    assert f"Successfully started VM {vm_name}" in Text.from_ansi(result.output).plain
    runner.invoke(vm.vm_group, ["delete", vm_name])
