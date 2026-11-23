from typing import Any

from cloudmesh.ai.vm.LibcloudManager import LibcloudManager
from cloudmesh.ai.vm.exceptions import (
    ProviderFeatureNotSupported,
    VMProviderError,
    VMResourceError,
)
from cloudmesh.ai.vm.logger import logger
# Ensure any exception messages are filtered for secrets.
from cloudmesh.ai.command._shared.providers_utils import sanitize_output

from libcloud.compute.providers import get_driver
from libcloud.compute.types import Provider as LibcloudProvider

GCEDriver = get_driver(LibcloudProvider.GCE)


class Provider(LibcloudManager):
    """
    Google Compute Engine implementation of the LibcloudManager.
    """

    def __init__(self, config, **kwargs):
        """Initialize the Google provider without forwarding cloud_name twice.

        The Cloudmesh provider factory may supply ``cloud_name`` in ``kwargs``.
        Remove it before passing the provider name to ``LibcloudManager`` to
        avoid a duplicate keyword argument error.
        """
        cloud_name = kwargs.pop("cloud_name", "google")
        super().__init__(config, cloud_name=cloud_name, **kwargs)

    def _get_driver(self):
        """Initialize the GCE driver with validated service-account settings."""
        cloud_config = self.get_cloud_config(self.cloud_name)

        required = (
            "service_account_email",
            "private_key",
            "project_id",
        )
        missing = [
            field
            for field in required
            if not isinstance(cloud_config.get(field), str)
            or not cloud_config[field].strip()
        ]

        if missing:
            raise VMProviderError(
                "Missing or invalid Google Cloud configuration: "
                + ", ".join(missing)
            )

        return GCEDriver(
            user_id=cloud_config["service_account_email"],
            key=cloud_config["private_key"],
            project=cloud_config["project_id"],
            auth_type="SA",
        )

    def assign_floating_ip(self, name: str) -> str | None:
        """
        Assigns a floating (static external) IP to the Google VM.
        """
        try:
            node = self.driver.get_node(name)
            if not node:
                raise VMResourceError(f"VM {name} not found in Google")

            cloud_config = self.get_cloud_config(self.cloud_name)
            region = cloud_config.get("region", "us-central1")

            # Reserve a static external IP
            address = self.driver.ex_create_address(name=f"ip-{name}", region=region)
            # Assign the static IP to the node
            # nic is typically 'nic0' for the primary interface
            self.driver.ex_add_access_config(
                node=node, name="external-nat", nic="nic0", nat_ip=address
            )

            return address
        except Exception as e:
            logger.error(f"Error assigning floating IP to {name} in Google: {e}")
            raise VMProviderError(f"Failed to assign floating IP to {name}: {e}")

    def release_floating_ip(self, name: str, release_allocation: bool = True) -> bool:
        """
        Releases the floating (static external) IP from the Google VM.
        """
        try:
            node = self.driver.get_node(name)
            if not node:
                raise VMResourceError(f"VM {name} not found in Google")

            public_ips = getattr(node, "public_ips", [])
            if not public_ips:
                logger.warning(f"No public IP found to release for VM {name}")
                return False

            address = public_ips[0]
            # Disassociate first
            self.driver.ex_delete_access_config(
                node=node, name="external-nat", nic="nic0"
            )
            # Release the address
            self.driver.ex_destroy_address(address=address)
            return True
        except Exception as e:
            logger.error(f"Error releasing floating IP from {name} in Google: {e}")
            safe_msg = sanitize_output(str(e))
            raise VMProviderError(f"Failed to release floating IP from {name}: {safe_msg}")

    def get_provider_info(self) -> dict[str, Any]:
        """Gets detailed information about the Google provider."""
        import subprocess

        version = "Unknown"
        try:
            result = subprocess.run(
                ["gcloud", "--version"], capture_output=True, text=True
            )
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

    def restart(self, name: str | None = None) -> bool:
        """Restarts a Google VM using the native reboot command."""
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
            logger.error(f"Error restarting Google VM {name}: {e}")
            return False

    def suspend(self, name: str | None = None) -> bool:
        """
        Suspends a Google VM. Tries native suspend first;
        falls back to stop to ensure compute resources are released.
        """
        if not name:
            return False
        try:
            node = self.driver.get_node(name)
            if not node:
                return False
            if hasattr(node, "suspend"):
                node.suspend()
                return True

            logger.info(
                f"Native suspend not supported for {name}. Falling back to stop..."
            )
            return self.stop(name)
        except Exception as e:
            logger.error(f"Error suspending Google VM {name}: {e}")
            return False

    def reset(self, name: str | None = None) -> bool:
        """
        Resets a Google VM. Performs a hard power cycle (stop -> start)
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
            logger.error(f"Error resetting Google VM {name}: {e}")
            return False

    # ---------------------------------------------------------------------
    # Console handling – Google Compute Engine provides a serial console via the
    # ``gcloud compute instances get-serial-port-output`` command.  For simplicity
    # and to avoid pulling in additional SDK calls, we raise ``ProviderFeatureNotSupported``
    # for any console request.  The CLI will then fall back to an SSH session.
    # ---------------------------------------------------------------------
    def get_console(self, vm_name: str, console_type: str = "text", **kwargs) -> str | None:
        """Return a console output or URL for a GCE VM.

        Currently only ``"text"`` is conceptually supported via the ``gcloud`` CLI.
        Because this repository does not depend on the ``gcloud`` binary in unit
        tests, we raise ``ProviderFeatureNotSupported`` and let the CLI fallback
        to SSH.  A future implementation could invoke ``gcloud`` or use the
        Compute Engine REST API to fetch the serial console output.
        """
        raise ProviderFeatureNotSupported(self.cloud_name, f"console:{console_type}")

# Compatibility alias for matrix tests and historic imports.
GoogleManager = Provider
