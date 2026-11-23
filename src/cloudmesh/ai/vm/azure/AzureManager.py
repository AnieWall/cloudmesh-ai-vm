from copy import deepcopy
from typing import Any

from cloudmesh.ai.vm.LibcloudManager import LibcloudManager
from cloudmesh.ai.vm.exceptions import (
    ConfigError,
    ProviderFeatureNotSupported,
    VMProviderError,
    VMResourceError,
)
from cloudmesh.ai.vm.logger import logger
# Sanitise any exception messages that may contain credentials.
from cloudmesh.ai.command._shared.providers_utils import sanitize_output

from libcloud.compute.providers import get_driver
from libcloud.compute.types import Provider as LibcloudProvider

AzureDriver = get_driver(LibcloudProvider.AZURE_ARM)


class Provider(LibcloudManager):
    """
    Azure implementation of the LibcloudManager.
    """

    def __init__(self, config, **kwargs):
        """Initialize the Azure provider without forwarding cloud_name twice.

        The Cloudmesh provider factory may supply ``cloud_name`` in ``kwargs``.
        Remove it before passing the provider name to ``LibcloudManager`` to
        avoid a duplicate keyword argument error.
        """
        cloud_name = kwargs.pop("cloud_name", "azure")
        super().__init__(config, cloud_name=cloud_name, **kwargs)

    def _get_driver(self):
        cloud_config = self.get_cloud_config("azure")
        return AzureDriver(
            tenant_id=cloud_config.get("tenant_id"),
            subscription_id=cloud_config.get("subscription_id"),
            key=cloud_config.get("client_id"),
            secret=cloud_config.get("client_secret"),
        )

    @staticmethod
    def _get_resource_group_from_id(resource_id: str) -> str:
        """Extract the resource group from an Azure resource ID."""
        if not isinstance(resource_id, str):
            raise VMProviderError("Invalid Azure resource ID")

        parts = resource_id.strip("/").split("/")

        for index, part in enumerate(parts):
            if part.lower() == "resourcegroups":
                if index + 1 < len(parts) and parts[index + 1]:
                    return parts[index + 1]
                break

        raise VMProviderError(
            f"Cannot determine resource group from Azure resource ID: "
            f"{resource_id}"
        )

    def _get_vm_nic(self, name: str):
        """Retrieve the single NIC attached to an Azure VM.

        Reject ambiguous networking configurations rather than modifying
        an unintended network interface or IP configuration.
        """
        node = self.get_vm(name)
        if node is None:
            raise VMResourceError(f"VM {name} not found in Azure")

        properties = getattr(node, "extra", {}).get("properties", {})
        network_profile = properties.get("networkProfile", {})
        nic_refs = network_profile.get("networkInterfaces") or []

        if len(nic_refs) != 1:
            raise VMProviderError(
                f"VM {name} must have exactly one attached NIC; "
                f"found {len(nic_refs)}"
            )

        nic_id = nic_refs[0].get("id")
        if not nic_id:
            raise VMProviderError(
                f"VM {name} has an attached NIC without a resource ID"
            )

        nic = self.driver.ex_get_nic(nic_id)
        if nic is None:
            raise VMResourceError(
                f"Attached NIC {nic_id} not found for VM {name}"
            )

        ip_configs = (getattr(nic, "extra", None) or {}).get(
            "ipConfigurations"
        ) or []

        if len(ip_configs) != 1:
            raise VMProviderError(
                f"NIC {nic_id} must have exactly one IP configuration; "
                f"found {len(ip_configs)}"
            )

        if not isinstance(ip_configs[0].get("properties"), dict):
            raise VMProviderError(
                f"NIC {nic_id} has an invalid IP configuration"
            )

        return node, nic

    def _is_managed_public_ip(self, public_ip) -> bool:
        """Verify Azure resource-level ownership tags for a public IP."""
        from libcloud.compute.drivers.azure_arm import TAG_API_VERSION

        response = self.driver.connection.request(
            public_ip.id,
            params={"api-version": TAG_API_VERSION},
        )

        resource = response.object
        if not isinstance(resource, dict):
            raise VMProviderError(
                "Azure returned invalid public IP resource metadata"
            )

        if resource.get("id", "").lower() != public_ip.id.lower():
            raise VMProviderError(
                "Azure public IP resource identity could not be verified"
            )

        tags = resource.get("tags") or {}
        if not isinstance(tags, dict):
            return False

        return (
            tags.get("cloudmesh-ai-vm:managed") == "true"
            and tags.get("cloudmesh-ai-vm:resource") == "public-ip"
        )

    def _get_public_ip_association(self, public_ip):
        """Read the current Azure association of a public IP resource.

        Return the attached IP configuration ID, or None if Azure
        explicitly reports the resource as unassociated.
        """
        current = self.driver.ex_get_public_ip(public_ip.id)
        if current is None:
            raise VMProviderError(
                f"Cannot verify public IP resource {public_ip.id}"
            )

        properties = getattr(current, "extra", None)
        if not isinstance(properties, dict):
            raise VMProviderError(
                f"Invalid public IP properties for {public_ip.id}"
            )

        association = properties.get("ipConfiguration")
        if association is None:
            return None

        if not isinstance(association, dict) or not association.get("id"):
            raise VMProviderError(
                f"Cannot determine public IP association for {public_ip.id}"
            )

        return association["id"]

    def _cleanup_unassociated_public_ip(self, public_ip, nic_id: str) -> bool:
        """Delete a new public IP only after verifying it is unattached.

        Fail closed: preserve the allocation if either Azure resource
        cannot be inspected or reports an association.
        """
        try:
            nic = self.driver.ex_get_nic(nic_id)
            if nic is None:
                return False

            properties = getattr(nic, "extra", None)
            if not isinstance(properties, dict):
                return False

            ip_configs = properties.get("ipConfigurations")
            if not isinstance(ip_configs, list) or not ip_configs:
                return False

            for ip_config in ip_configs:
                if not isinstance(ip_config, dict):
                    return False

                config_properties = ip_config.get("properties")
                if not isinstance(config_properties, dict):
                    return False

                association = config_properties.get("publicIPAddress")
                if association is not None:
                    if not isinstance(association, dict):
                        return False
                    if not association.get("id"):
                        return False
                    if association["id"].lower() == public_ip.id.lower():
                        return False

            if self._get_public_ip_association(public_ip) is not None:
                return False

            deleted = self.driver.ex_delete_public_ip(public_ip)
            if not deleted:
                logger.warning(
                    "Azure did not confirm deletion of public IP %s",
                    public_ip.id,
                )
                return False

            return True

        except Exception as exc:
            logger.warning(
                f"Preserving public IP {public_ip.id} because cleanup "
                f"could not be verified: {sanitize_output(str(exc))}"
            )
            return False

    def assign_floating_ip(self, name: str) -> str | None:
        """Assign a managed Azure public IP to the VM's existing NIC."""
        public_ip = None
        nic_id = None

        try:
            node, nic = self._get_vm_nic(name)
            nic_id = nic.id

            if getattr(node, "public_ips", None):
                raise VMProviderError(
                    f"VM {name} already has a public IP"
                )

            properties = deepcopy(nic.extra)
            ip_config = properties["ipConfigurations"][0]["properties"]

            if ip_config.get("publicIPAddress") is not None:
                raise VMProviderError(
                    f"NIC {nic.id} already has a public IP association"
                )

            cloud_config = self.get_cloud_config(self.cloud_name)
            resource_group = cloud_config.get("resource_group")
            if not resource_group:
                raise ConfigError(
                    "Missing 'resource_group' in Azure config"
                )

            public_ip = self.driver.ex_create_public_ip(
                name=f"pip-{name}",
                resource_group=resource_group,
            )

            self.driver.ex_create_tags(
                public_ip,
                {
                    "cloudmesh-ai-vm:managed": "true",
                    "cloudmesh-ai-vm:resource": "public-ip",
                },
            )

            if not self._is_managed_public_ip(public_ip):
                raise VMProviderError(
                    f"Cannot verify ownership of public IP {public_ip.id}"
                )

            ip_config["publicIPAddress"] = {"id": public_ip.id}

            self.driver.ex_update_nic_properties(
                network_interface=nic,
                resource_group=self._get_resource_group_from_id(nic.id),
                properties=properties,
            )

            current_nic = self.driver.ex_get_nic(nic_id)
            if current_nic is None:
                raise VMProviderError(
                    "Cannot verify Azure NIC update"
                )

            current_configs = (
                (getattr(current_nic, "extra", None) or {})
                .get("ipConfigurations") or []
            )

            if len(current_configs) != 1:
                raise VMProviderError(
                    "Cannot verify Azure NIC IP configuration"
                )

            association = (
                current_configs[0].get("properties", {})
                .get("publicIPAddress") or {}
            )

            if (
                not isinstance(association, dict)
                or association.get("id", "").lower()
                != public_ip.id.lower()
            ):
                raise VMProviderError(
                    "Azure NIC public IP association was not confirmed"
                )

            current_ip = self.driver.ex_get_public_ip(public_ip.id)
            address = (
                (getattr(current_ip, "extra", None) or {})
                .get("ipAddress")
                if current_ip is not None
                else None
            )

            return address if isinstance(address, str) else None

        except Exception as exc:
            if public_ip is not None and nic_id is not None:
                cleaned = self._cleanup_unassociated_public_ip(
                    public_ip, nic_id
                )
                if not cleaned:
                    logger.warning(
                        f"Public IP {public_ip.id} was preserved; "
                        "manual reconciliation may be required"
                    )

            safe_msg = sanitize_output(str(exc))
            raise VMProviderError(
                f"Failed to assign floating IP to {name}: {safe_msg}"
            ) from exc

    def release_floating_ip(self, name: str, release_allocation: bool = True) -> bool:
        """Safely detach and release a Cloudmesh-managed Azure public IP."""
        try:
            node, nic = self._get_vm_nic(name)

            nic_properties = deepcopy(nic.extra)
            ip_config = nic_properties["ipConfigurations"][0]
            config_properties = ip_config["properties"]

            association = config_properties.get("publicIPAddress")
            if not isinstance(association, dict) or not association.get("id"):
                logger.warning(f"No public IP association found for VM {name}")
                return False

            public_ip_id = association["id"]
            public_ip = self.driver.ex_get_public_ip(public_ip_id)

            if public_ip is None or public_ip.id.lower() != public_ip_id.lower():
                raise VMProviderError(
                    "Azure public IP resource identity could not be verified"
                )

            if not self._is_managed_public_ip(public_ip):
                raise VMProviderError(
                    f"Public IP {public_ip_id} is not managed by "
                    "cloudmesh-ai-vm; refusing to detach or delete it"
                )

            ip_properties = getattr(public_ip, "extra", None)
            if not isinstance(ip_properties, dict):
                raise VMProviderError(
                    f"Cannot verify public IP association for {public_ip_id}"
                )

            resource_association = ip_properties.get("ipConfiguration")
            if not isinstance(resource_association, dict):
                raise VMProviderError(
                    f"Cannot verify public IP association for {public_ip_id}"
                )

            resource_config_id = resource_association.get("id")
            expected_prefix = nic.id.rstrip("/") + "/ipConfigurations/"

            if (
                not isinstance(resource_config_id, str)
                or not resource_config_id.lower().startswith(
                    expected_prefix.lower()
                )
            ):
                raise VMProviderError(
                    f"Public IP {public_ip_id} is not verified as attached "
                    f"to VM {name}'s NIC"
                )

            # Remove only the public IP association. Preserve every other
            # NIC and IP configuration property.
            config_properties.pop("publicIPAddress")

            cloud_config = self.get_cloud_config(self.cloud_name)
            resource_group = cloud_config.get("resource_group")

            if not resource_group:
                raise ConfigError(
                    "Missing 'resource_group' in Azure config"
                )

            self.driver.ex_update_nic_properties(
                network_interface=nic,
                resource_group=self._get_resource_group_from_id(nic.id),
                properties=nic_properties,
            )

            # Independently verify the NIC no longer references this IP.
            current_nic = self.driver.ex_get_nic(nic.id)
            if current_nic is None:
                raise VMProviderError(
                    "Cannot verify NIC after public IP detachment"
                )

            current_configs = (
                (getattr(current_nic, "extra", None) or {})
                .get("ipConfigurations")
            )

            if not isinstance(current_configs, list) or len(current_configs) != 1:
                raise VMProviderError(
                    "Cannot verify NIC IP configuration after detachment"
                )

            current_properties = current_configs[0].get("properties")
            if not isinstance(current_properties, dict):
                raise VMProviderError(
                    "Invalid NIC properties after public IP detachment"
                )

            remaining = current_properties.get("publicIPAddress")
            if remaining is not None:
                raise VMProviderError(
                    "Azure NIC still reports a public IP association"
                )

            # Independently verify that Azure has removed the reverse
            # association from the public IP resource.
            current_ip = self.driver.ex_get_public_ip(public_ip_id)
            if current_ip is None or current_ip.id.lower() != public_ip_id.lower():
                raise VMProviderError(
                    "Cannot verify public IP resource after detachment"
                )

            if self._get_public_ip_association(current_ip) is not None:
                raise VMProviderError(
                    "Azure public IP remains associated; refusing deletion"
                )

            if not self.driver.ex_delete_public_ip(current_ip):
                raise VMProviderError(
                    f"Azure did not confirm deletion of public IP {public_ip_id}"
                )

            return True

        except Exception as exc:
            logger.error(
                f"Error releasing public IP from Azure VM {name}: {exc}"
            )
            safe_msg = sanitize_output(str(exc))
            raise VMProviderError(
                f"Failed to release floating IP from {name}: {safe_msg}"
            ) from exc

    def get_provider_info(self) -> dict[str, Any]:
        """Gets detailed information about the Azure provider."""
        cloud_config = self.get_cloud_config(self.cloud_name)
        return {
            "provider": "Azure",
            "cloud_name": self.cloud_name,
            "version": self.version,
            "config": {
                "subscription_id": cloud_config.get("subscription_id"),
                "tenant_id": cloud_config.get("tenant_id"),
            },
        }

    def restart(self, name: str | None = None) -> bool:
        """Restarts an Azure VM using the native reboot command."""
        if not name:
            return False
        try:
            node = self.driver.get_node(name)
            if not node:
                return False
            if hasattr(node, "reboot"):
                node.reboot()
                return True
            if hasattr(self.driver, "reboot_node"):
                self.driver.reboot_node(node)
                return True
            raise ProviderFeatureNotSupported(self.cloud_name, "restart")
        except Exception as e:
            if isinstance(e, ProviderFeatureNotSupported):
                raise e
            logger.error(f"Error restarting Azure VM {name}: {e}")
            return False

    def suspend(self, name: str | None = None) -> bool:
        """
        Suspends an Azure VM. In Azure, this is mapped to 'stop' (deallocate)
        to release compute resources and stop billing.
        """
        if not name:
            return False
        try:
            return self.stop(name)
        except Exception as e:
            logger.error(f"Error suspending Azure VM {name}: {e}")
            return False

    def reset(self, name: str | None = None) -> bool:
        """
        Resets an Azure VM. Performs a hard power cycle (stop -> start)
        if the native restart fails.
        """
        if not name:
            return False
        try:
            # 1. Try the soft restart first
            if self.restart(name):
                return True

            # 2. Fallback: Hard Power Cycle
            logger.info(
                f"Native restart failed for {name}. Performing hard reset (stop -> start)..."
            )
            if self.stop(name):
                return self.start(name=name)
            return False
        except Exception as e:
            logger.error(f"Error resetting Azure VM {name}: {e}")
            return False

    # ---------------------------------------------------------------------
    # Console handling – Azure does not provide a simple text console via the
    # libcloud driver used in this repository.  Raising ``ProviderFeatureNotSupported``
    # signals the CLI to fall back to SSH access, matching the behaviour of other
    # providers that cannot expose a console endpoint.
    # ---------------------------------------------------------------------
    def get_console(self, vm_name: str, console_type: str = "text", **kwargs) -> str | None:
        """Return a console URL or plain‑text output for an Azure VM.

        Currently this implementation does not retrieve any console
        information and always raises ``ProviderFeatureNotSupported``.  The
        abstract method requirement is satisfied, and additional logic can be
        added later if Azure console support becomes necessary.
        """
        raise ProviderFeatureNotSupported(self.cloud_name, f"console:{console_type}")

# Compatibility alias for matrix tests and historic imports.
AzureManager = Provider
