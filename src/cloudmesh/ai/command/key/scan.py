import click
import json
import os
import webbrowser
from cloudmesh.ai.command._shared.context import console
from cloudmesh.ai.command._shared.exceptions import handle_errors
from cloudmesh.ai.command._shared.ui import render_table
from cloudmesh.ai.vm.key_manager import KeyManager

@click.command()
@click.option("--json", "as_json", is_flag=True, help="Output in JSON format")
@handle_errors
def scan(as_json: bool):
    """Lists all found local SSH keys, their types, fingerprints, and whether they have passphrases."""
    km = KeyManager()
    keys = km.scan_local_keys()

    if not keys:
        console.print("No local SSH keys found.")
        return

    if as_json:
        console.print(json.dumps(keys, indent=2))
        return

    home = os.path.expanduser("~")
    rows = []
    for k in keys:
        path = k["path"]
        if path.startswith(home):
            path = path.replace(home, "~", 1)
        rows.append([path, k["type"], k["sha256"], k["md5"], k["comment"], "Yes" if k["has_passphrase"] else "No"])

    render_table("Local SSH Keys", ["Path", "Type", "Fingerprint (SHA256)", "Fingerprint (MD5)", "Comment", "Passphrase"], rows)

    # Identify keys without passphrases
    unprotected_keys = [k["path"].replace(home, "~", 1) if k["path"].startswith(home) else k["path"]
                        for k in keys if not k["has_passphrase"]]

    if unprotected_keys:
        console.print("\n[bold red]The following keys are unprotected (no passphrase):[/bold red]")
        for key_path in unprotected_keys:
            console.print(f" - [red]{key_path}[/red]")

        console.print("\n[bold yellow]WARNING:[/bold yellow] The keys listed above are local SSH keys. They [bold red]must not[/bold red] be used for cloud providers such as [bold]AWS, Azure, Google, Chameleon, or Jetstream[/bold].")
        console.print("For cloud providers, it is strongly recommended to [bold]create a dedicated key with a passphrase[/bold] and manage it using [bold]ssh-agent[/bold] for better security.")

cmd = scan
