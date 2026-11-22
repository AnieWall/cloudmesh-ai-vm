"""Base VM provider interface.

This module defines :class:`BaseVMProvider`, the abstract base class that all VM
providers must implement. The original implementation used ``builtins.list``
type hints to avoid clashing with provider‐specific ``list`` methods. With
Python 3.15+ the native generic ``list`` syntax is available, so the hints have
been updated accordingly and the ``import builtins`` statement removed.
"""

from abc import ABC
from typing import Any, Dict, List

from .exceptions import ProviderFeatureNotSupported


class BaseVMProvider(ABC):
    """Abstract Base Class for all VM providers.

    Ensures a consistent interface across different cloud providers.
    """

    def __init__(self, config: Any):
        self.config = config
        self.cloud_name = "base"

    def validate_config(self) -> Dict[str, List[str]]:
        """Validates the provider configuration.

        Returns a map of config paths to error lists. The return type uses the
        native ``list`` generic to avoid clashing with any subclass that defines a
        method named ``list``.
        """
        return {}

    def normalize_vm_info(self, vm_info: dict[str, Any]) -> dict[str, Any]:
        """Normalizes VM info keys to lowercase."""
        return {k.lower(): v for k, v in vm_info.items()}

    def exists(self, name: str) -> bool:
        """Checks if a VM with the given name exists in the provider.

        The default implementation uses ``list_instances()`` to verify existence.
        """
        try:
            vms = self.list_instances()
            if not vms:
                return False
            # Check for name matches (case‑insensitive)
            return any(
                str(vm.get("name")).lower() == name.lower()
                for vm in vms
                if isinstance(vm, dict)
            )
        except Exception:
            # Return False to avoid noisy stack traces in stop/delete if listing fails
            return False

    # --- Lifecycle Methods ---
    def start(
        self,
        name: str | None = None,
        flavor: str | None = None,
        image: str | None = None,
        **kwargs,
    ) -> str:
        raise ProviderFeatureNotSupported(self.cloud_name, "start")

    def stop(self, name: str | None = None) -> bool:
        raise ProviderFeatureNotSupported(self.cloud_name, "stop")

    def restart(self, name: str | None = None) -> bool:
        raise ProviderFeatureNotSupported(self.cloud_name, "restart")

    def reset(self, name: str | None = None) -> bool:
        raise ProviderFeatureNotSupported(self.cloud_name, "reset")

    def suspend(self, name: str | None = None) -> bool:
        raise ProviderFeatureNotSupported(self.cloud_name, "suspend")

    def delete(self, name: str | None = None) -> bool:
        raise ProviderFeatureNotSupported(self.cloud_name, "delete")

    def login(self, name: str | None = None) -> bool:
        """Logs into a VM."""
        raise ProviderFeatureNotSupported(self.cloud_name, "login")

    def run_command(self, name: str, cmd: str) -> str:
        raise ProviderFeatureNotSupported(self.cloud_name, "run_command")

    def shelve(self, name: str | None = None) -> bool:
        raise ProviderFeatureNotSupported(self.cloud_name, "shelve")

    def unshelve(self, name: str | None = None) -> bool:
        raise ProviderFeatureNotSupported(self.cloud_name, "unshelve")

    # --- Inventory Methods ---
    def list_instances(self) -> list[dict[str, Any]]:
        """Lists all VMs in the cloud.

        This replaces the historic ``list()`` method to avoid shadowing the built‑in
        ``list`` type. Sub‑classes should implement ``list_instances``; a
        compatibility shim ``list`` is provided below for legacy callers.
        """
        raise ProviderFeatureNotSupported(self.cloud_name, "list_instances")

    def list(self, **kwargs) -> list[dict[str, Any]]:
        """Compatibility shim – delegates to ``list_instances`` if not overridden."""
        return self.list_instances(**kwargs)

    def get_console_connection_keys(self, vm: dict[str, Any]) -> dict[str, str] | None:
        """Retrieves connection details like SSH keys for a given VM."""
        raise ProviderFeatureNotSupported(self.cloud_name, "get_console_connection_keys")

    def get_flavors(self, **kwargs) -> list[dict[str, Any]]:
        """Lists instance flavors/sizes."""
        raise ProviderFeatureNotSupported(self.cloud_name, "list_flavors")

    def get_images(self, **kwargs) -> list[dict[str, Any]]:
        """Lists available VM images."""
        raise ProviderFeatureNotSupported(self.cloud_name, "list_images")

    def get_keys(self) -> list[dict[str, Any]]:
        """Lists available SSH keys."""
        raise ProviderFeatureNotSupported(self.cloud_name, "list_keys")

    def upload_key(self, key_path: str, key_name: str, vm_name: str | None = None) -> bool:
        """Uploads a public key."""
        raise ProviderFeatureNotSupported(self.cloud_name, "upload_key")

    def delete_key(self, key_name: str, vm_name: str | None = None) -> bool:
        """Deletes a public key from the cloud provider.

        Optional ``vm_name`` for providers that manage keys per‑VM.
        """
        raise ProviderFeatureNotSupported(self.cloud_name, "delete_key")

    def get_security_groups(self) -> list[dict[str, Any]]:
        """Lists available security groups."""
        raise ProviderFeatureNotSupported(self.cloud_name, "get_security_groups")

    def get_security_group_info(self, name: str) -> dict[str, Any]:
        """Gets detailed information for a specific security group."""
        raise ProviderFeatureNotSupported(self.cloud_name, "get_security_group_info")

    def create_security_group(self, name: str, description: str = "") -> bool:
        """Creates a security group in the cloud."""
        raise ProviderFeatureNotSupported(self.cloud_name, "create_security_group")

    def delete_security_group(self, name: str) -> bool:
        """Deletes a security group from the cloud."""
        raise ProviderFeatureNotSupported(self.cloud_name, "delete_security_group")

    def add_security_group_to_vm(self, vm_name: str, sg_name: str) -> bool:
        """Associates a security group with a VM."""
        raise ProviderFeatureNotSupported(self.cloud_name, "add_security_group_to_vm")

    def remove_security_group_from_vm(self, vm_name: str, sg_name: str) -> bool:
        """Removes a security group association from a VM."""
        raise ProviderFeatureNotSupported(self.cloud_name, "remove_security_group_from_vm")

    def add_security_group_rule(
        self,
        sg_name: str,
        protocol: str,
        port: str,
        cidr: str,
        direction: str = "ingress",
    ) -> str:
        """Adds a firewall rule to a security group. Returns the rule ID."""
        raise ProviderFeatureNotSupported(self.cloud_name, "add_security_group_rule")

    def remove_security_group_rule(self, sg_name: str, rule_id: str) -> bool:
        """Removes a specific rule from a security group using its ID."""
        raise ProviderFeatureNotSupported(self.cloud_name, "remove_security_group_rule")

    def list_security_group_rules(self, sg_name: str) -> list[dict[str, Any]]:
        """Lists all rules for a specific security group."""
        raise ProviderFeatureNotSupported(self.cloud_name, "list_security_group_rules")

    # --- Network Methods ---
    def list_regions(self) -> list[dict[str, Any]]:
        """Lists available regions."""
        raise ProviderFeatureNotSupported(self.cloud_name, "list_regions")

    def assign_floating_ip(self, name: str) -> str | None:
        """Assigns a floating IP to the VM."""
        raise ProviderFeatureNotSupported(self.cloud_name, "assign_floating_ip")

    def release_floating_ip(self, name: str) -> bool:
        """Releases a floating IP from the VM."""
        raise ProviderFeatureNotSupported(self.cloud_name, "release_floating_ip")

    # --- Cost Methods ---
    def get_cost(self, **kwargs) -> Any | None:
        """Calculates the cost for a VM configuration."""
        raise ProviderFeatureNotSupported(self.cloud_name, "get_cost")
