import click
import json
from .._shared.context import console
from .._shared.exceptions import handle_errors
from .._shared.ui import render_table
from cloudmesh.ai.vm.key_manager import KeyManager

@click.command()
@click.option("--json", "as_json", is_flag=True, help="Output in JSON format")
@handle_errors
def scan(as_json: bool):
    """Lists all found local SSH keys, their types, and whether they have passphrases."""
    km = KeyManager()
    keys = km.scan_local_keys()

    if not keys:
        console.print("No local SSH keys found.")
        return

    if as_json:
        console.print(json.dumps(keys, indent=2))
        return

    rows = [[k["path"], k["type"], "Yes" if k["has_passphrase"] else "No"] for k in keys]
    render_table("Local SSH Keys", ["Path", "Type", "Passphrase"], rows)

@click.command()
@click.option("--json", "as_json", is_flag=True, help="Output in JSON format")
@handle_errors
def verify(as_json: bool):
    """Checks which local keys currently authenticate with GitHub."""
    km = KeyManager()
    local_keys = km.scan_local_keys()

    if not local_keys:
        console.print("No local SSH keys found to verify.")
        return

    results = []
    with console.status("[bold green]Verifying GitHub authentication..."):
        for key in local_keys:
            path = key["path"]
            auth_status = km.verify_github_auth(path)
            results.append({
                "path": path,
                "authenticated": auth_status
            })

    if as_json:
        console.print(json.dumps(results, indent=2))
        return

    rows = [[r["path"], "Yes" if r["authenticated"] else "No"] for r in results]
    render_table("GitHub Authentication Status", ["Path", "Authenticated"], rows)
