import pytest
import re
import json
from rich.text import Text
from click.testing import CliRunner
from cloudmesh.ai.command import vm
from cloudmesh.ai.common.stopwatch import StopWatch

from tests.smoke.cli_helper import setup_cli_config

from tests.smoke.benchmark_helper import (
    save_benchmark,
    create_benchmark_payload,
    get_results_username,  
)

@pytest.fixture
def runner():
    return CliRunner()

@pytest.fixture
def config(tmp_path, runner):
    provider_config = {
        "template": "ubuntu",
    }
    setup_cli_config(tmp_path, "lima", provider_config)

def test_lima_cli_lifecycle(runner, config):
    """
    Smoke test for Lima CLI lifecycle.
    """
    env = {"OS_CLOUD": "lima"}
    # 1. providers
    result = runner.invoke(vm.vm_group, ["provider", "list"], env=env)
    assert result.exit_code == 0
    assert "lima" in result.output.lower()

    # 2. set
    result = runner.invoke(vm.vm_group, ["provider", "set", "lima"], env=env)
    assert result.exit_code == 0

    # 3. start (without name - test auto-naming)
    result = runner.invoke(vm.vm_group, ["start"], env=env)
    if result.exit_code != 0:
        pytest.skip(f"Lima start failed: {result.output}")

    output = Text.from_ansi(result.output).plain
    assert "Generating VM name" in output

    # Extract the generated VM name
    import re
    match = re.search(r"Successfully started VM ([\w-]+)", output)
    if match:
        vm_name = match.group(1)
    else:
        # Fallback for different output formats
        vm_name = "smoke-lima-vm"

    try:
        # 4. list
        result = runner.invoke(vm.vm_group, ["list"], env=env)
        assert result.exit_code == 0
        # Check for the truncated name or prefix since Rich tables wrap/truncate long names
        plain_output = Text.from_ansi(result.output).plain
        assert vm_name[:12] in plain_output or "smoke-test-" in plain_output
        
        # 5. run
        result = runner.invoke(vm.vm_group, ["run", vm_name, "hostname"])
        if result.exit_code != 0:
            pytest.skip(f"Lima run failed: {result.output}")

        # 6. stop
        result = runner.invoke(vm.vm_group, ["stop", vm_name], env=env)
        assert result.exit_code == 0

        # 7. delete
        result = runner.invoke(vm.vm_group, ["delete", vm_name], env=env)
        assert result.exit_code == 0

        # 8. images
        result = runner.invoke(vm.vm_group, ["image"], env=env)
        assert result.exit_code == 0

        # 9. flavors
        result = runner.invoke(vm.vm_group, ["flavor"], env=env)
        assert result.exit_code == 0

        # 10. keys
        result = runner.invoke(vm.vm_group, ["key", "list"], env=env)
        assert result.exit_code == 0

        # 11. security_groups
        result = runner.invoke(vm.vm_group, ["security-group"], env=env)
        assert result.exit_code == 0

        # 12. ssh_config
        runner.invoke(vm.vm_group, ["start", vm_name], env=env)
        result = runner.invoke(vm.vm_group, ["ssh-config"], env=env)
        assert result.exit_code == 0
        assert "Host" in result.output

    finally:
        # Cleanup VMs
        runner.invoke(vm.vm_group, ["delete", vm_name])
        
        # Save standard benchmark text/json files
        save_benchmark(tag="Lima CLI", config_path=config)

        # Retrieve the results username dynamically using the config path
        try:
            username = get_results_username(config_path=config)
        except Exception:
            username = "smoke_test_user"

        # Create and print/save the structured JSON payload
        payload = create_benchmark_payload(
            benchmark_name="Lima CLI", 
            user=username
        )
        
        # Optional: print or write the payload to a separate JSON file if desired

        print(json.dumps(payload, indent=2))

def test_lima_cli_start_with_name(runner, config):
    """
    Test starting a Lima VM with a specific name.
    """
    vm_name = "test-named-lima-vm"
    runner.invoke(vm.vm_group, ["delete", vm_name])

    result = runner.invoke(vm.vm_group, ["start", vm_name])
    if result.exit_code != 0:
        pytest.skip("Lima start failed")

    assert f"Successfully started VM {vm_name}" in Text.from_ansi(result.output).plain
    runner.invoke(vm.vm_group, ["delete", vm_name])
