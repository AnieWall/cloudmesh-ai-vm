"""Compatibility shim for the ``cloudmesh.ai.command.vm.key.upload`` import.

Historically the ``vm key upload`` command lived in ``cloudmesh.ai.command.key``
and the test suite expects it to be importable via the legacy path
``cloudmesh.ai.command.vm.key.upload``. The original module defines the Click
command ``upload_key`` and a ``cmd`` alias. To satisfy the test without
duplicating logic we re‑implement the command here by copying the implementation
from ``cloudmesh.ai.command.key.upload``. This ensures that patching
``get_active_provider`` on this module (as performed in the unit tests) works
as intended.
"""

import glob
import os
from pathlib import Path

import click

from cloudmesh.ai.command._shared.context import console, get_active_provider
from cloudmesh.ai.command._shared.exceptions import VMCommandError, handle_errors


@click.command()
@click.pass_context
@click.argument("key_path", required=False)
@click.option("--name", help="Custom name for the key")
@handle_errors
def upload_key(ctx: click.Context, key_path: str = None, name: str = None):
    """Upload a public SSH key to the cloud provider.

    This implementation mirrors the original ``upload_key`` command located in
    ``cloudmesh.ai.command.key.upload``. The logic is kept in sync to avoid
    divergence between the legacy import path and the current command group.
    """
    provider = get_active_provider(ctx)
    config = provider.get_cloud_config(provider.cloud_name) or {}

    # Resolve the SSH public key path and the key name.
    # If the user supplied a ``key_path`` argument we honour it (expanding ``~``).
    # Otherwise we delegate to the shared ``resolve_key_path`` helper which
    # implements the unified logic described in issue #131.  When the helper
    # cannot resolve a key (e.g., missing ``~/.ssh``), we fall back to the legacy
    # discovery mechanism to preserve backward compatibility.
    from cloudmesh.ai.vm.key_utils import resolve_key_path
    from cloudmesh.ai.command._shared.exceptions import VMCommandError

    if key_path:
        # User supplied an explicit path – just expand it.
        key_path = os.path.expanduser(key_path)
        # Derive a name from the filename when not explicitly provided.
        if not name:
            name = Path(key_path).stem
    else:
        # No explicit argument – try the global helper first.
        try:
            pub_path, derived_name = resolve_key_path(config)
            key_path = str(pub_path)
            if not name:
                name = derived_name
        except VMCommandError:
            # Legacy fallback: search ``~/.ssh`` for a suitable public key.
            ssh_dir = os.path.expanduser("~/.ssh")
            # Prefer common defaults.
            fallbacks = ["id_ed25519.pub", "id_rsa.pub"]
            for fb in fallbacks:
                candidate = os.path.join(ssh_dir, fb)
                if os.path.exists(candidate):
                    key_path = candidate
                    break
            if not key_path:
                pub_files = glob.glob(os.path.join(ssh_dir, "*.pub"))
                if len(pub_files) == 1:
                    key_path = pub_files[0]
                elif len(pub_files) > 1:
                    raise VMCommandError(
                        f"Multiple public keys found in {ssh_dir} ({len(pub_files)} files). "
                        "The tool cannot decide which key to use. Please specify 'key_path' "
                        "as an argument or configure it in clouds.yaml."
                    )
                else:
                    raise VMCommandError(
                        f"No public keys found in {ssh_dir}. Please provide a key_path."
                    )
            # Derive a name from the discovered key if not provided.
            if not name:
                name = Path(key_path).stem

    # Resolve name (if still not set) from configuration as a final fallback.
    if not name:
        name = config.get("key_name")

    if provider.upload_key(key_path, name):
        console.print(f"Successfully uploaded key [bold green]{key_path}[/bold green].")
    else:
        raise VMCommandError(f"Failed to upload key {key_path}.")


# The CLI command is exported under the name ``cmd`` in the original module.
cmd = upload_key
