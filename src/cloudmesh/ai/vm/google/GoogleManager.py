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

    def start(self, name: Optional[str] = None, flavor: Optional[str] = None, image: Optional[str] = None) -> str:
        """
        Starts a Google Compute Engine VM using libcloud.
        """
        from cloudmesh.ai.vm.logger import logger

        cloud_config = self.get_cloud_config("google")
        image_name = image or cloud_config.get("image")
        flavor_name = flavor or cloud_config.get("flavor") or cloud_config.get("size")

        if not image_name:
            raise ValueError(f"Missing 'image' in config or arguments for {self.cloud_name}")
        if not flavor_name:
            raise ValueError(f"Missing 'flavor' or 'size' in config or arguments for {self.cloud_name}")

        try:
            # Find image object
            all_images = self.driver.list_images()
            img = next((i for i in all_images if i.name == image_name), None)
            if not img:
                raise RuntimeError(f"Could not find image {image_name} in {self.cloud_name}")

            # Find flavor/size object
            all_flavors = self.driver.list_sizes()
            flv = next((f for f in all_flavors if f.name == flavor_name), None)
            if not flv:
                raise RuntimeError(f"Could not find flavor {flavor_name} in {self.cloud_name}")

            vm_name = name or f"vm-{self.cloud_name}"
            logger.info(f"Starting Google VM {vm_name} with image {image_name} and flavor {flavor_name}...")

            node = self.driver.create_node(name=vm_name, image=img, size=flv)
            logger.info(f"Successfully started Google VM {vm_name} (ID: {node.id})")

            return node.id
        except Exception as e:
            logger.error(f"Libcloud start failed for {self.cloud_name}: {e}")
            raise e

    @property
    def version(self) -> List[str]:
        """Returns the provider version."""
        try:
            import libcloud
            return [f"libcloud: {libcloud.__version__}"]
        except Exception:
            return ["libcloud: Unknown"]

