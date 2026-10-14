import os
import click
from cloudmesh.ai.command._shared.utils import load_commands_recursively

@click.group()
def key_group() -> None:
    """Key management commands"""
    pass

# Initialize the dynamic loading
COMMANDS_DIR = os.path.dirname(__file__)
load_commands_recursively(key_group, COMMANDS_DIR, "cloudmesh.ai.command.key")
