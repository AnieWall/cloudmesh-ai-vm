import click
import json
from .._shared.context import console
from .._shared.exceptions import handle_errors
from .._shared.ui import render_table
from cloudmesh.ai.vm.key_manager import KeyManager

@click.group()
def github():
    """Manage SSH keys on GitHub."""
    pass

@github.command()
@click.argument("key_path", type=click.Path(exists=True))
@handle_errors
def upload(key_path):
    """Uploads a specific local key to GitHub."""
    km = KeyManager()
    with console.status(f"[bold green]Uploading {key_path} to GitHub..."):
        result = km.github_upload(key_path)

    if result["success"]:
        console.print(f"[bold green]Successfully uploaded key:[/bold green] {result['output']}")
    else:
        console.print(f"[bold red]Failed to upload key:[/bold red] {result['error']}")

@github.command()
@click.option("--json", "as_json", is_flag=True, help="Output in JSON format")
@handle_errors
def list(as_json: bool):
    """Lists the keys currently configured in GitHub."""
    km = KeyManager()
    with console.status("[bold green]Fetching keys from GitHub..."):
        keys = km.github_list()

    if not keys:
        console.print("No SSH keys found on GitHub.")
        return

    if as_json:
        console.print(json.dumps(keys, indent=2))
        return

    rows = [[k["name"], k["fingerprint"], k["type"]] for k in keys]
    render_table("GitHub SSH Keys", ["Name", "Fingerprint", "Type"], rows)

cmd = github
