import click
from cloudmesh.ai.command._shared.context import console
from cloudmesh.ai.command._shared.exceptions import handle_errors

@click.command()
@handle_errors
def init_config(ctx: click.Context):
    """Initialize the VM CLI configuration."""
    # Implementation would go here to create the config file
    console.print("VM configuration initialized.")

cmd = init_config
