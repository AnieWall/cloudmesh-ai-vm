from typing import List, Dict, Any, Optional
from cloudmesh.ai.vm.LibcloudManager import LibcloudManager

try:
    from libcloud.compute.providers.gce import GCEDriver
except ImportError:
    class GCEDriver:
        def __init__(self, *args, **kwargs): pass

class Provider(LibcloudManager):
    """
    Google Compute Engine implementation of the LibcloudManager.
    """

    def __init__(self, config, **kwargs):
        super().__init__(config, cloud_name="google", **kwargs)

    def _get_driver(self):
        cloud_config = self.get_cloud_config("google")
        return GCEDriver(
            project_id=cloud_config.get("project_id"),
            private_key=cloud_config.get("private_key")
        )

    def get_provider_info(self) -> Dict[str, Any]:
        """Gets detailed information about the Google provider."""
        return {
            "provider": "Google",
            "cloud_name": self.cloud_name,
            "version": self.version,
        }

    def wait_for_status(self, name: str, target_status: str, timeout: int = 300) -> bool:
        """
        Polls the Google VM status until it matches target_status.
        """
        import time
        from cloudmesh.ai.vm.logger import logger

        logger.info(f"Waiting for Google VM {name} to reach status {target_status}...")
        start_time = time.time()

        while time.time() - start_time < timeout:
            node = self.driver.get_node(name)
            if node:
                current_status = getattr(node, 'state', '').lower()
                if current_status == target_status.lower():
                    logger.info(f"VM {name} reached status {target_status}.")
                    return True

            time.sleep(5)

        logger.error(f"Timeout reached waiting for Google VM {name} to reach status {target_status}.")
        return False

