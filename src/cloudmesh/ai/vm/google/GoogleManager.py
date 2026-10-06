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
        import subprocess

        version = "Unknown"
        try:
            result = subprocess.run(["gcloud", "--version"], capture_output=True, text=True)
            if result.returncode == 0:
                # gcloud --version returns multiple lines, take the first one
                version = result.stdout.splitlines()[0].strip()
        except Exception:
            pass

        cloud_config = self.get_cloud_config(self.cloud_name)
        return {
            "provider": "Google",
            "cloud_name": self.cloud_name,
            "version": version,
            "config": {
                "project_id": cloud_config.get("project_id"),
            },
        }


