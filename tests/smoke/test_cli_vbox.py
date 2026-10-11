import pytest
import re
from rich.text import Text
from click.testing import CliRunner
from cloudmesh.ai.command import vm
from tests.smoke.cli_helper import setup_cli_config

@pytest.fixture
def runner():
    return CliRunner()

@pytest.fixture
def config(tmp_path, runner):
    provider_config = {
        "image": "ubuntu",
    }
    setup_cli_config(tmp_path, "vbox", provider_config)

def test_vbox_cli_lifecycle(runner, config):
    """
    Smoke test for VBox CLI lifecycle.
    """
    # 1. providers
    result = runner.invoke(vm.vm_group, ["provider", "list"])
    assert result.exit_code == 0
    assert "vbox" in result.output.lower()

    # 2. set
    result = runner.invoke(vm.vm_group, ["provider", "set", "vbox"])
    assert result.exit_code == 0

    # 3. start (without name)
    result = runner.invoke(vm.vm_group, ["start"])
    if result.exit_code != 0:
        # VBox might not be installed or configured in the test env, skip if so
        pytest.skip(f"VBox start failed: {result.output}")

    output = Text.from_ansi(result.output).plain
    assert "Generating VM name" in output

    # Extract the generated VM name
    match = re.search(r"Successfully started VM ([\w-]+)", output)
    vm_name = match.group(1) if match else "smoke-vbox-vm"

    try:
        # 4. list
        result = runner.invoke(vm.vm_group, ["list"])
        assert result.exit_code == 0
        assert vm_name.lower() in Text.from_ansi(result.output).plain.lower()

        # 5. stop
        result = runner.invoke(vm.vm_group, ["stop", vm_name])
        assert result.exit_code == 0

        # 6. delete
        result = runner.invoke(vm.vm_group, ["delete", vm_name])
        assert result.exit_code == 0

        # 7. images
        result = runner.invoke(vm.vm_group, ["image"])
        assert result.exit_code == 0

        # 8. flavors
        result = runner.invoke(vm.vm_group, ["flavor"])
        assert result.exit_code == 0

        # 9. keys
        result = runner.invoke(vm.vm_group, ["key"])
        assert result.exit_code == 0

    finally:
        # Cleanup
        runner.invoke(vm.vm_group, ["delete", vm_name])

def test_vbox_cli_start_with_name(runner, config):
    """
    Test starting a VBox VM with a specific name.
    """
    vm_name = "test-named-vbox-vm"
    runner.invoke(vm.vm_group, ["delete", vm_name])

    result = runner.invoke(vm.vm_group, ["start", vm_name])
    if result.exit_code != 0:
        pytest.skip("VBox start failed")

    assert f"Successfully started VM {vm_name}" in Text.from_ansi(result.output).plain
    runner.invoke(vm.vm_group, ["delete", vm_name])
