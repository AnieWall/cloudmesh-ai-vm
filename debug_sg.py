import os
import click.testing
from cloudmesh.ai.command.vm import vm_group

def test_sg():
    runner = click.testing.CliRunner()
    os.environ["OS_CLOUD"] = "chameleon"
    result = runner.invoke(vm_group, ["security_groups"])
    print(f"Exit Code: {result.exit_code}")
    print(f"Output:\n{result.output}")
    print(f"Exception:\n{result.exception}")

if __name__ == "__main__":
    test_sg()
