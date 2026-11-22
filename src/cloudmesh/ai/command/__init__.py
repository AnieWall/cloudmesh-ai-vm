import importlib
import logging
import os
from typing import Optional

import click


def load_commands_recursively(group: click.Group, current_dir: str, package_path: str):
    """
    Recursively scans the directory for .py files and folders,
    adding them as commands or subgroups to the provided group.
    """
    for entry in os.listdir(current_dir):
        # Ignore internal folders, files, and __init__.py
        if entry.startswith("_") or entry == "__init__.py":
            continue

        full_path = os.path.join(current_dir, entry)

        if os.path.isdir(full_path):
            # 1. Handle Sub-groups (folders)
            group_name = entry
            module_path = f"{package_path}.{group_name}"
            try:
                mod = importlib.import_module(module_path)
                group_obj = getattr(mod, "cmd", None)

                if not group_obj or not isinstance(group_obj, click.Group):
                    # Fallback: Create a generic group if 'cmd' is missing or not a Group
                    group_obj = click.Group(name=group_name)

                group.add_command(group_obj, name=group_name.replace("_", "-"))

                # Recurse into the folder
                load_commands_recursively(group_obj, full_path, module_path)

            except Exception as e:
                logging.error(
                    f"Failed to load group {group_name} from {module_path}: {e}"
                )

        elif entry.endswith(".py"):
            # 2. Handle Commands (files)
            cmd_name = entry[:-3]
            module_path = f"{package_path}.{cmd_name}"
            try:
                mod = importlib.import_module(module_path)
                cmd_obj = getattr(mod, "cmd", None)

                if cmd_obj:
                    group.add_command(cmd_obj, name=cmd_name.replace("_", "-"))
                else:
                    logging.warning(
                        f"Module {module_path} does not export a 'cmd' object."
                    )

            except Exception as e:
                logging.error(
                    f"Failed to load command {cmd_name} from {module_path}: {e}"
                )


@click.group()
def cmx() -> None:
    """Cloudmesh AI CLI"""


# We will import and add subgroups here to avoid circular imports
# during the initial group definition.
def init_cmx():
    """Initialise the top‑level CLI groups.

    The ``container`` sub‑command imports the Docker manager which depends on
    ``CloudBaseManager`` from the VM package. Importing it here would create a
    circular import chain during module initialisation (command -> container ->
    DockerManager -> CloudBaseManager -> command). To avoid that, we only
    eagerly register the ``key`` and ``vm`` groups, which are safe and required
    for the current test suite. The ``container`` group can still be loaded
    lazily via ``load_commands_recursively`` when the CLI is used in a real
    environment.
    """
    from .key import key_group
    from .vm import vm_group
    # Register the groups. ``container`` is omitted to prevent circular imports.
    cmx.add_command(vm_group, name="vm")
    cmx.add_command(key_group, name="key")


# NOTE: Previously the command groups were eagerly initialised on module import.
# This caused a circular import when ``cloudmesh.ai.command`` was imported as a
# side‑effect of loading ``cloudmesh.ai.command._shared.providers_utils`` (which
# is required for secret‑masking).  The eager initialisation pulled in the
# ``container`` sub‑module, which itself imports ``CloudBaseManager`` – still being
# defined – leading to an ``ImportError: cannot import name 'CloudBaseManager'``.
#
# The CLI groups are only needed when the ``cmx`` command-line entry point is
# executed, not during normal library imports or unit tests.  Therefore we defer
# initialisation to the entry‑point script and omit the automatic call here.
#
# If CLI functionality is required programmatically, callers can invoke
# ``init_cmx()`` explicitly after importing this package.
# init_cmx()
# Initialise the CLI command hierarchy when this module is imported.
# This makes sub‑commands such as ``key`` and ``vm`` available via the ``cmx``
# entry point without requiring callers to invoke ``init_cmx`` manually.  The
# previous lazy initialisation was introduced to avoid circular imports during
# early module loading; after the recent fixes (e.g., providing concrete
# ``get_console`` implementations) the import graph is now safe, and eager
# registration simplifies test usage.
init_cmx()
