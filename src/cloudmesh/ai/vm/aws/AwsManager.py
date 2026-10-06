from typing import List, Dict, Any, Optional
from cloudmesh.ai.vm.LibcloudManager import LibcloudManager

try:
    from libcloud.compute.providers.amazon import AmazonEC2Driver
except ImportError:
    class AmazonEC2Driver:
        def __init__(self, *args, **kwargs): pass

class Provider(LibcloudManager):
    """
    AWS EC2 implementation of the LibcloudManager.
    """

    def __init__(self, config, **kwargs):
        super().__init__(config, cloud_name="aws", **kwargs)

    def _get_driver(self):
        cloud_config = self.get_cloud_config("aws")
        return AmazonEC2Driver(
            access_key=cloud_config.get("access_key"),
            secret_key=cloud_config.get("secret_key"),
            region=cloud_config.get("region", "us-east-1")
        )

    def get_provider_info(self) -> Dict[str, Any]:
        """Gets detailed information about the AWS provider."""
        import subprocess

        version = "Unknown"
        try:
            result = subprocess.run(["aws", "--version"], capture_output=True, text=True)
            if result.returncode == 0:
                version = result.stdout.strip()
        except Exception:
            pass

        cloud_config = self.get_cloud_config(self.cloud_name)
        region = cloud_config.get("region", "us-east-1")

        account_id = "Unknown"
        try:
            result = subprocess.run(
                ["aws", "sts", "get-caller-identity", "--query", "Account", "--output", "text"],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                account_id = result.stdout.strip()
        except Exception:
            pass

        return {
            "provider": "AWS",
            "cloud_name": self.cloud_name,
            "version": version,
            "config": {
                "region": region,
                "account_id": account_id,
            },
        }

