import pytest
import re
from rich.text import Text
from click.testing import CliRunner
from cloudmesh.ai.command import vm
from tests.smoke.cli_helper import setup_cli_config
from tests.smoke.benchmark_helper import save_benchmark
from cloudmesh.ai.common.stopwatch import StopWatch

@pytest.fixture
def runner():
    return CliRunner()

@pytest.fixture
def config(tmp_path, runner):
    provider_config = {
        "image": "22.04",
    }
    # This uses "smoke_test_user" which tests the underscore -> hyphen sanitization
    setup_cli_config(tmp_path, "multipass", provider_config)

def test_multipass_cli_lifecycle(runner, config):
    """
    Smoke test for Multipass CLI lifecycle.
    """
    # 1. providers
    result = runner.invoke(vm.vm_group, ["provider", "list"])
    assert result.exit_code == 0
    assert "multipass" in result.output.lower()

    # 2. set
    result = runner.invoke(vm.vm_group, ["provider", "set", "multipass"])
    assert result.exit_code == 0

    # 3. start (without name)
    # Should generate a name like smoke-test-user-1
    with StopWatch.timer("multipass_start"):
        result = runner.invoke(vm.vm_group, ["start"])
    if result.exit_code != 0:
        # Multipass might not be installed in the test env, skip if so
        pytest.skip(f"Multipass start failed: {result.output}")


    assert "Generating VM name" in result.output
    # Verify the underscore was replaced by hyphen: smoke_test_user -> smoke-test-user
    assert "smoke-test-user-" in result.output

    # Extract the generated VM name for subsequent steps
    output = Text.from_ansi(result.output).plain
    match = re.search(r"Successfully started VM ([\w-]+)", output)
    vm_name = match.group(1) if match else "smoke-test-user"

    try:
        # 4. list
        with StopWatch.timer("multipass_list"):
            result = runner.invoke(vm.vm_group, ["list"])
        assert result.exit_code == 0
        # Verify the new header: "VMs on multipass"
        assert "VMs on multipass" in result.output
        # Use a case-insensitive check or check if vm_name is in output
        assert vm_name.lower() in result.output.lower()

        # 5. run
        with StopWatch.timer("multipass_run"):
            result = runner.invoke(vm.vm_group, ["run", "hostname"])
        assert result.exit_code == 0

        # 6. stop
        with StopWatch.timer("multipass_stop"):
            result = runner.invoke(vm.vm_group, ["stop", vm_name])
        assert result.exit_code == 0

        # 7. delete
        with StopWatch.timer("multipass_delete"):
            result = runner.invoke(vm.vm_group, ["delete", vm_name])
        assert result.exit_code == 0

        # 8. images
        with StopWatch.timer("multipass_images"):
            result = runner.invoke(vm.vm_group, ["image"])
        assert result.exit_code == 0

        # 9. flavors
        with StopWatch.timer("multipass_flavors"):
            result = runner.invoke(vm.vm_group, ["flavor"])
        assert result.exit_code == 0

        # 10. keys
        with StopWatch.timer("multipass_keys"):
            result = runner.invoke(vm.vm_group, ["key"])
        assert result.exit_code == 0


    finally:
        # Cleanup
        runner.invoke(vm.vm_group, ["delete", vm_name])
        save_benchmark(tag="Multipass CLI", config_path=None)

def test_multipass_cli_start_with_name(runner, config):
    """
    Test starting a VM with a specific name.
    """
    vm_name = "test-named-vm"
    runner.invoke(vm.vm_group, ["delete", vm_name])

    result = runner.invoke(vm.vm_group, ["start", vm_name])
    if result.exit_code != 0:
        pytest.skip("Multipass start failed")

    # Use a more flexible check for the success message to avoid ANSI color issues
    assert f"Successfully started VM {vm_name}" in Text.from_ansi(result.output).plain
    runner.invoke(vm.vm_group, ["delete", vm_name])
