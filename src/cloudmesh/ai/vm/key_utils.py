"""Utility functions for handling SSH key resolution.

This module provides a single public helper ``resolve_key_path`` used by the
OpenStack‑based providers (OpenstackManager and ChameleonManager) to locate the
SSH public key file and determine the appropriate key name to use when creating
or uploading a keypair.

The logic mirrors the behaviour that previously existed as duplicated code in
the two manager classes. It centralises the handling of the following cases:

1. **Explicit ``key_path``** – If the user provides a ``key_path`` in the
   provider configuration, the function expands ``~`` to the user's home
   directory, validates that the file exists, and derives the key name.  An
   explicit ``key_name`` in the configuration overrides the derived name.
2. **Implicit default** – When ``key_path`` is not supplied, the function looks
   for a ``~/.ssh`` directory. If the directory does not exist, a
   ``VMCommandError`` is raised.  It then searches for ``*.pub`` files:

   * No public keys → error.
   * Exactly one public key → that key is used.
   * Multiple public keys → error instructing the user to provide ``key_path``
     or ``key_name``.

The function returns a tuple ``(key_path: Path, key_name: str)``.  Errors are
raised as ``VMCommandError`` (imported from ``cloudmesh.ai.command._shared``) so
that calling code can handle them uniformly.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Tuple

# ``VMCommandError`` is the canonical exception type used throughout the CLI for
# user‑facing command errors. Importing it here avoids a circular import because
# the key utilities are only used by provider classes, not by the exception
# module itself.
from cloudmesh.ai.command._shared.exceptions import VMCommandError


def resolve_key_path(config: dict) -> Tuple[Path, str]:
    """Resolve the SSH public key location and name.

    Parameters
    ----------
    config:
        Provider configuration dictionary. May contain ``key_path`` and
        ``key_name`` entries.

    Returns
    -------
    Tuple[Path, str]
        ``(key_path, key_name)`` where ``key_path`` is a ``Path`` instance
        pointing to the public key file and ``key_name`` is the name to use for
        the keypair in the cloud.

    Raises
    ------
    VMCommandError
        If the key cannot be resolved due to missing files, ambiguous matches,
        or absent ``~/.ssh`` directory.
    """

    # 1. Explicit key_path provided in configuration.
    key_path_cfg = config.get("key_path")
    explicit_key_name = config.get("key_name")

    if key_path_cfg is not None:
        # Expand ``~`` and any environment variables.
        expanded_path = os.path.expanduser(key_path_cfg)
        if not os.path.isfile(expanded_path):
            raise VMCommandError(
                f"Explicit SSH public key path does not exist: {expanded_path}"
            )
        key_path = Path(expanded_path)
        # Derive the key name: config overrides, otherwise use filename without ``.pub``.
        key_name = explicit_key_name or key_path.stem
        return key_path, key_name

    # 2. No explicit key_path – attempt to locate a default key in ``~/.ssh``.
    ssh_dir = os.path.expanduser("~/.ssh")
    if not os.path.isdir(ssh_dir):
        raise VMCommandError(
            f"SSH directory not found at expected location: {ssh_dir}. "
            "Provide a 'key_path' in your provider configuration."
        )

    # Search for public key files.
    pub_keys = list(Path(ssh_dir).glob("*.pub"))
    if not pub_keys:
        raise VMCommandError(
            f"No SSH public keys found in {ssh_dir}. Provide a 'key_path' in configuration."
        )
    if len(pub_keys) > 1:
        names = ", ".join(p.name for p in pub_keys)
        raise VMCommandError(
            f"Multiple SSH public keys found in {ssh_dir}: {names}. "
            "Specify which one to use via 'key_path' (or set 'key_name' to rename)."
        )

    key_path = pub_keys[0]
    key_name = explicit_key_name or key_path.stem
    return key_path, key_name
