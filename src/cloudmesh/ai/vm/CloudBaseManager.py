from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from rich.text import Text
from .base import BaseVMProvider

class CloudBaseManager(BaseVMProvider, ABC):
    """
    Abstract Base Class for Cloud VM Managers.
    All cloud providers (OpenStack, Multipass, etc.) must implement this interface.
    """

    def __init__(self, config: Any, console=None, **kwargs):
        super().__init__(config)
        self.console = console

    def get_cloud_config(self, cloud_name: str) -> Dict[str, Any]:
        """
        Helper to retrieve configuration for a specific cloud, 
        handling both dictionary, StateManager, and GlobalConfig object inputs.
        """
        # 1. Handle StateManager (YamlDB)
        if hasattr(self.config, "get_cloud_config") and callable(getattr(self.config, "get_cloud_config")):
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
    
    def start(self, name: Optional[str] = None, flavor: Optional[str] = None, image: Optional[str] = None) -> str:
        """Starts a VM."""
        return super().start(name)

    def stop(self, name: Optional[str] = None) -> bool:
        """Stops a VM."""
        return super().stop(name)

    def delete(self, name: Optional[str] = None) -> bool:
        """Deletes a VM."""
        return super().delete(name)

    def list(self) -> List[Dict[str, Any]]:
        """Lists all VMs managed by this provider."""
        return super().list()

    def login(self, name: Optional[str] = None) -> bool:
        """Logs into a VM."""
        return super().login(name)

    def suspend(self, name: Optional[str] = None) -> bool:
        """Suspends a VM."""
        return super().suspend(name)

    def shelve(self, name: Optional[str] = None) -> bool:
        """Shelves a VM."""
        return super().shelve(name)

    def unshelve(self, name: Optional[str] = None) -> bool:
        """Unshelves a VM."""
        return super().unshelve(name)

    def restart(self, name: Optional[str] = None) -> bool:
        """Restarts a VM."""
        return super().restart(name)

    def reset(self, name: Optional[str] = None) -> bool:
        """Resets a VM or the provider service."""
        return super().reset(name)

    def info(self, name: str) -> Dict[str, Any]:
        """Gets detailed information about a specific VM."""
        return super().info(name)

    def get_security_groups(self) -> List[Dict[str, Any]]:
        """Lists available security groups for the current cloud."""
        return super().get_security_groups()

    def upload_key(self, key_path: str, key_name: str) -> bool:
        """Uploads a public key to the cloud provider."""
        return super().upload_key(key_path, key_name)

    def delete_key(self, key_name: str) -> bool:
        """Deletes a public key from the cloud provider."""
        return super().delete_key(key_name)

    def get_cost(self, **kwargs) -> Optional[Any]:
        """Returns the cost information for the provider."""
        return None

    def validate_config(self) -> Dict[str, List[str]]:
        """Validates that the cloud configuration has all required fields."""
        return {}
    def get_account_info(self) -> Dict[str, Any]:
        """Returns account and quota information for the current provider."""
        return {"error": "Account information not supported for this provider."}


    def add_security_group_rule(
        self,
        sg_name: str,
        protocol: str,
        port: str,
        cidr: str,
        direction: str = "ingress",
    ) -> str:
        """Adds a firewall rule to a security group."""
        return super().add_security_group_rule(
            sg_name, protocol, port, cidr, direction
        )

    def _execute_ssh_command(self, ip: str, user: str, key_path: str, command: str) -> str:
        """
        Generic SSH command executor.
        """
        import subprocess
        import os

        key_path = os.path.expanduser(key_path)

        ssh_cmd = [
            "ssh",
            "-i", key_path,
            "-o", "StrictHostKeyChecking=no",
            "-o", "UserKnownHostsFile=/dev/null",
            f"{user}@{ip}",
            command
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
        """Helper to print output using the associated rich console if available."""
        if self.console:
            self.console.print(*args, **kwargs)
        else:
            print(*args, **kwargs)

    def print_ansi(self, text: str, **kwargs):
        """Prints text and cleans up ANSI sequences and CLI spinner artifacts."""
        if self.console:
            self.console.print(Text.from_ansi(text), **kwargs)
        else:
            print(text, **kwargs)

    def _run_interactive(self, command: List[str]):
        """Runs a command directly connected to the terminal for smooth animations."""
        import subprocess
        try:
            return subprocess.run(command, capture_output=False, check=True)
        except subprocess.CalledProcessError as e:
            raise e
