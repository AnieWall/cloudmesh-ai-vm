import builtins
import os
from abc import ABC
from pathlib import Path
from typing import Any

import yaml
from rich import print as rprint
from rich.pretty import Pretty
from rich.text import Text

# The sanitiser removes any credential‑like fragments from strings that will be
# displayed to the user.  By applying it to ``print_ansi`` we guarantee that even
# rich‑console output cannot leak secrets.
from cloudmesh.ai.command._shared.providers_utils import sanitize_output

from .base import BaseVMProvider


class CloudBaseManager(BaseVMProvider, ABC):
    """
    Abstract Base Class for Cloud VM Managers.
    All cloud providers (OpenStack, Multipass, etc.) must implement this interface.
    """

    def DEBUG(self, message: Any):
        if isinstance(message, dict):
            # Pretty print the dictionary with syntax highlighting
            rprint(Pretty(message))
        else:
            # Print non-dict messages in bold blue
            rprint(Text(str(message), style="bold blue"))

    def __init__(self, config: Any, console=None, **kwargs):
        super().__init__(config)
        self.console = console

    def _get_default_vm(self, cloud_name: str = "chameleon") -> str | None:
        """
        Attempts to retrieve the last used or default VM name for the specified cloud
        from cloudmesh configuration or a local state file.
        """
        # 1. Check if a local state file (e.g., ~/.config/cloudmesh/last_vm.<cloud_name>) exists
        state_file = Path(
            os.path.expanduser(f"~/.config/cloudmesh/last_vm.{cloud_name}")
        )
        if state_file.exists():
            vm_name = state_file.read_text().strip()
            if vm_name:
                return vm_name

        # 2. Fallback: Read from ~/.config/cloudmesh/clouds.yaml if applicable
        config_path = Path(os.path.expanduser("~/.config/cloudmesh/clouds.yaml"))
        if config_path.exists():
            try:
                with open(config_path, "r") as f:
                    config_data = yaml.safe_load(f)
                    # Check for a default VM configured under the specific cloud or profile
                    clouds = config_data.get("clouds", {})
                    cloud_cfg = clouds.get(cloud_name, {})
                    if isinstance(cloud_cfg, dict):
                        default_vm = cloud_cfg.get("default_vm")
                        if default_vm:
                            return default_vm
            except Exception as e:
                self.DEBUG(f"Error reading clouds.yaml: {e}")

        return None

    def get_cloud_config(self, cloud_name: str) -> dict[str, Any]:
        """
        Helper to retrieve configuration for a specific cloud,
        handling both dictionary, StateManager, and GlobalConfig object inputs.
        """
        # 1. Handle StateManager (YamlDB)
        if hasattr(self.config, "get_cloud_config") and callable(
            self.config.get_cloud_config
        ):
            return self.config.get_cloud_config(cloud_name)

        # 2. Handle plain dictionary
        if isinstance(self.config, dict):
            return self.config.get("clouds", {}).get(cloud_name, {})

        # 3. Handle GlobalConfig object (dataclass)
        clouds = getattr(self.config, "clouds", {})
        if isinstance(clouds, dict):
            cloud_cfg = clouds.get(cloud_name, {})
        else:
            # Fallback if clouds is not a dict
            return {}

        # If the cloud_cfg is a dataclass (ProviderConfig), convert to dict
        if not isinstance(cloud_cfg, dict) and hasattr(cloud_cfg, "__dict__"):
            return cloud_cfg.__dict__

        return cloud_cfg if isinstance(cloud_cfg, dict) else {}

    # We remove @abstractmethod from methods that are not mandatory for all providers.
    # BaseVMProvider already provides default implementations that raise ProviderFeatureNotSupported.

    def start(
        self,
        name: str | None = None,
        flavor: str | None = None,
        image: str | None = None,
        **kwargs,
    ) -> str:
        """Starts a VM."""
        return super().start(name, flavor=flavor, image=image, **kwargs)

    def stop(self, name: str | None = None) -> bool:
        """Stops a VM."""
        return super().stop(name)

    def delete(self, name: str | None = None) -> bool:
        """Deletes a VM."""
        return super().delete(name)

    def list(self) -> list[dict[str, Any]]:
        """Lists all VMs managed by this provider."""
        return super().list()

    def login(self, name: str | None = None) -> bool:
        """Logs into a VM."""
        return super().login(name)

    def suspend(self, name: str | None = None) -> bool:
        """Suspends a VM."""
        return super().suspend(name)

    def shelve(self, name: str | None = None) -> bool:
        """Shelves a VM."""
        return super().shelve(name)

    def unshelve(self, name: str | None = None) -> bool:
        """Unshelves a VM."""
        return super().unshelve(name)

    def restart(self, name: str | None = None) -> bool:
        """Restarts a VM."""
        return super().restart(name)

    def reset(self, name: str | None = None) -> bool:
        """Resets a VM or the provider service."""
        return super().reset(name)

    def info(self, name: str | None = None, kind: str = "vm") -> dict[str, Any]:
        """
        Gets detailed information about a specific VM.
        If name is missing, attempts to read it from the last_vm state file
        or cloudmesh configuration.
        """
        if not name:
            cloud_name = getattr(self, "cloud_name", "chameleon")
            name = self._get_default_vm(cloud_name)

            if not name:
                self.print(
                    f"[red]Error: Missing argument 'NAME' and no default VM found for cloud '{cloud_name}'.[/red]"
                )
                return {}

            self.print(
                f"[yellow]No VM name provided. Using default/last VM: {name}[/yellow]"
            )

        # Delegate to the underlying provider implementation (or super class)
        return super().info(name, kind=kind)

    def get_security_groups(self) -> list[dict[str, Any]]:
        """Lists available security groups for the current cloud."""
        return super().get_security_groups()

    def upload_key(self, key_path: str, key_name: str) -> bool:
        """Uploads a public key to the cloud provider."""
        return super().upload_key(key_path, key_name)

    def delete_key(self, key_name: str, vm_name: str | None = None) -> bool:
        """Deletes a public key from the cloud provider."""
        return super().delete_key(key_name, vm_name=vm_name)

    def get_cost(self, **kwargs) -> Any | None:
        """Returns the cost information for the provider."""
        return None

    def validate_config(self) -> dict[str, list[str]]:
        """Validates that the cloud configuration has all required fields."""
        return {}

    def _get_current_status(self, name: str) -> str:
        """Returns the current status of the VM. Must be implemented by child classes."""
        raise ProviderFeatureNotSupported(self.cloud_name, "_get_current_status")

    def _normalize_status(self, status: str) -> str:
        """Normalizes the status string for comparison."""
        return status.lower() if status else ""

    def wait_for_status(
        self, name: str, target_status: str, timeout: int = 300
    ) -> bool:
        """
        Polls the VM status until it matches the target_status or the timeout is reached.
        Returns True if the status was reached, False otherwise.
        """
        import time

        from cloudmesh.ai.vm.logger import logger

        logger.info(f"Waiting for VM {name} to reach status {target_status}...")
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                current_status = self._get_current_status(name)
                if current_status:
                    normalized_current = self._normalize_status(current_status)
                    normalized_target = self._normalize_status(target_status)
                    if normalized_current == normalized_target:
                        logger.info(f"VM {name} reached status {target_status}.")
                        return True
            except Exception as e:
                logger.error(f"Error polling status for VM {name}: {e}")

            time.sleep(5)

        logger.error(
            f"Timeout reached waiting for VM {name} to reach status {target_status}."
        )
        return False

    def add_security_group_rule(
        self,
        sg_name: str,
        protocol: str,
        port: str,
        cidr: str,
        direction: str = "ingress",
    ) -> str:
        """Adds a firewall rule to a security group."""
        return super().add_security_group_rule(sg_name, protocol, port, cidr, direction)

    def _execute_ssh_command(
        self, ip: str, user: str, key_path: str, command: str
    ) -> str:
        """
        Generic SSH command executor.
        """
        import os
        import subprocess

        key_path = os.path.expanduser(key_path)

        ssh_cmd = [
            "ssh",
            "-i",
            key_path,
            "-o",
            "StrictHostKeyChecking=no",
            "-o",
            "UserKnownHostsFile=/dev/null",
            f"{user}@{ip}",
            command,
        ]

        try:
            result = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                return f"SSH Error (code {result.returncode}): {result.stderr}"
            return result.stdout.strip()
        except subprocess.TimeoutExpired:
            return "SSH Error: Command timed out after 30 seconds"
        except Exception as e:
            return f"SSH Error: Unexpected error executing command: {e}"

    def print(self, *args, **kwargs):
        """Helper to print output using the associated rich console if available.

        All string arguments are passed through ``sanitize_output`` to ensure that
        no credential‑like fragments are written to the console or stdout.
        """
        # Convert each argument to a string and sanitise it.
        safe_args = [sanitize_output(str(a)) for a in args]
        if self.console:
            self.console.print(*safe_args, **kwargs)
        else:
            print(*safe_args, **kwargs)

    def print_ansi(self, text: str, **kwargs):
        """Prints text and cleans up ANSI sequences and CLI spinner artifacts.

        The string is first passed through ``sanitize_output`` to strip any
        embedded secrets (tokens, passwords, etc.) before it reaches the console
        or stdout.
        """
        safe_text = sanitize_output(text)
        if self.console:
            self.console.print(Text.from_ansi(safe_text), **kwargs)
        else:
            print(safe_text, **kwargs)

    # ---------------------------------------------------------------------
    # CLI execution helper with secret masking
    # ---------------------------------------------------------------------
    def _run_cli_and_mask(self, *args, **kwargs):
        """Execute a CLI command while ensuring any exception message is
        stripped of credential‑like fragments.

        Provider subclasses (e.g., :class:`OpenstackManager`) implement their own
        ``_run_command`` method.  This helper delegates to that method and then
        sanitises any raised exception using ``sanitize_output`` before re‑raising
        a :class:`VMProviderError`.  Centralising the logic here guarantees that
        all providers benefit from consistent secret‑masking without needing to
        duplicate the implementation.
        """
        from cloudmesh.ai.command._shared.providers_utils import sanitize_output
        from cloudmesh.ai.vm.exceptions import VMProviderError

        try:
            result = self._run_command(*args, **kwargs)
            # ``_run_command`` raises on non‑zero exit codes, but when mocked it
            # can return an object with a ``returncode`` attribute. Guard against
            # that scenario as well.
            if hasattr(result, "returncode") and result.returncode != 0:
                raise VMProviderError("CLI command failed")
            return result
        except Exception as e:
            safe_msg = sanitize_output(str(e))
            raise VMProviderError(f"CLI command failed: {safe_msg}") from e

    def _run_interactive(self, command: builtins.list[str]):
        """Runs a command directly connected to the terminal for smooth animations."""
        import subprocess

        try:
            return subprocess.run(command, capture_output=False, check=True)
        except subprocess.CalledProcessError as e:
            raise e
