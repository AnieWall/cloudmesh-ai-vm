from typing import List, Dict, Any, Optional
from cloudmesh.ai.vm.LibcloudManager import LibcloudManager

try:
    from libcloud.compute.providers.azure import AzureDriver
except ImportError:
    class AzureDriver:
        def __init__(self, *args, **kwargs): pass

class Provider(LibcloudManager):
    """
    Azure implementation of the LibcloudManager.
    """

    def __init__(self, config, **kwargs):
        super().__init__(config, cloud_name="azure", **kwargs)

    def _get_driver(self):
        cloud_config = self.get_cloud_config("azure")
        return AzureDriver(
            tenant_id=cloud_config.get("tenant_id"),
            subscription_id=cloud_config.get("subscription_id"),
            client_id=cloud_config.get("client_id"),
            client_secret=cloud_config.get("client_secret")
        )

    def assign_floating_ip(self, name: str) -> Optional[str]:
        """
        Assigns a floating (public) IP to the Azure VM.
        """
        try:
            node = self.driver.get_node(name)
            if not node:
                raise VMResourceError(f"VM {name} not found in Azure")

            cloud_config = self.get_cloud_config(self.cloud_name)
            resource_group = cloud_config.get("resource_group")
            subnet = cloud_config.get("subnet")

            if not resource_group:
                raise ConfigError("Missing 'resource_group' in Azure config")
            if not subnet:
                raise ConfigError("Missing 'subnet' in Azure config")

            # Allocate a new public IP address
            public_ip = self.driver.ex_create_public_ip(name=f"pip-{name}", resource_group=resource_group)
            # Associate the public IP via a network interface
            self.driver.ex_create_network_interface(
                name=f"nic-{name}",
                subnet=subnet,
                resource_group=resource_group,
                public_ip=public_ip
            )

            return public_ip
        except Exception as e:
            logger.error(f"Error assigning floating IP to {name} in Azure: {e}")
            raise VMProviderError(f"Failed to assign floating IP to {name}: {e}")

    def release_floating_ip(self, name: str) -> bool:
        """
        Releases the floating (public) IP from the Azure VM.
        """
        try:
            node = self.driver.get_node(name)
            if not node:
                raise VMResourceError(f"VM {name} not found in Azure")

            public_ips = getattr(node, 'public_ips', [])
            if not public_ips:
                logger.warning(f"No public IP found to release for VM {name}")
                return False

            public_ip = public_ips[0]
            self.driver.ex_delete_public_ip(public_ip=public_ip)
            return True
        except Exception as e:
            logger.error(f"Error releasing floating IP from {name} in Azure: {e}")
            raise VMProviderError(f"Failed to release floating IP from {name}: {e}")

    def get_provider_info(self) -> Dict[str, Any]:
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

    def restart(self, name: Optional[str] = None) -> bool:
        """Restarts an Azure VM."""
        if not name:
            return False
        try:
            node = self.driver.get_node(name)
            if not node:
                return False
            if hasattr(node, 'reboot'):
                node.reboot()
                return True
            if hasattr(self.driver, 'reboot_node'):
                self.driver.reboot_node(node)
                return True
            raise ProviderFeatureNotSupported(self.cloud_name, "restart")
        except Exception as e:
            if isinstance(e, ProviderFeatureNotSupported):
                raise e
            return False

    def suspend(self, name: Optional[str] = None) -> bool:
        """Suspends (Deallocates) an Azure VM."""
        if not name:
            return False
        try:
            # In Azure, suspend is effectively stop/deallocate
            return self.stop(name)
        except Exception:
            return False

    def reset(self, name: Optional[str] = None) -> bool:
        """Resets an Azure VM (Hard reboot)."""
        if not name:
            return False
        try:
            if self.restart(name):
                return True
            if self.stop(name):
                return self.start(name=name)
            return False
        except Exception:
            return False


