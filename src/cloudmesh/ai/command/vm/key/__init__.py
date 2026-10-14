import click
from .local import scan, verify
from .github import github as github_group

@click.group()
def key_group():
    """Manage VM SSH keys."""
    pass

key_group.add_command(scan)
key_group.add_command(verify)
key_group.add_command(github_group, name="github")

cmd = key_group
