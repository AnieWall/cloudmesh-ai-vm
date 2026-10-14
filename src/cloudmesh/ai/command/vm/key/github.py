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

    rows = []
    for k in keys:
        key_str = k.get("key", "")
        key_type = "Unknown"
        if key_str.startswith("ssh-rsa"):
            key_type = "rsa"
        elif key_str.startswith("ssh-ed25519"):
            key_type = "ed25519"
        elif key_str.startswith("ssh-dss"):
            key_type = "dsa"
        elif key_str.startswith("ecdsa-sha2-nistp"):
            key_type = "ecdsa"

        rows.append([
            k.get("title", "N/A"),
            key_type,
            k.get("sha256", "N/A"),
            k.get("md5", "N/A"),
            k.get("created_at", "N/A"),
            k.get("last_used", "N/A"),
            "Yes" if k.get("verified") else "No",
            k.get("local_path", "N/A")
        ])

    render_table("GitHub SSH Keys", ["Name", "Type", "SHA256 Fingerprint", "MD5 Fingerprint", "Created At", "Last Used", "Verified", "Local Path"], rows)

@github.command()
@click.option("--json", "as_json", is_flag=True, help="Output in JSON format")
@handle_errors
def verify(as_json: bool):
    """Checks which local keys are registered with GitHub."""
    km = KeyManager()
    local_keys = km.scan_local_keys()

    if not local_keys:
        console.print("No local SSH keys found to verify.")
        return

    results = []
    with console.status("[bold green]Verifying GitHub authentication..."):
        for key in local_keys:
            path = key["path"]
            auth_info = km.verify_github_auth(path)

            results.append({
                "path": path,
                "authenticated": auth_info["authenticated"],
                "title": auth_info["title"],
                "fingerprint": auth_info["fingerprint"],
                "created_at": auth_info["created_at"],
                "last_used": auth_info["last_used"]
            })

    if as_json:
        console.print(json.dumps(results, indent=2))
        return

    rows = [[r["path"], "Yes" if r["authenticated"] else "No", r["title"] or "N/A", r["fingerprint"] or "N/A", r["created_at"], r["last_used"]] for r in results]
    render_table("GitHub Authentication Status", ["Path", "Authenticated", "GitHub Name", "Fingerprint", "Created At", "Last Used"], rows)

cmd = github
