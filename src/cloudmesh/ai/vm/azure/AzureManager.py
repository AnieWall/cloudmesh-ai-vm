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


