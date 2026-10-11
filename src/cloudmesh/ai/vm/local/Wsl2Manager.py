import subprocess
import re
import shutil
from typing import List, Dict, Any, Optional
from ..LocalBaseManager import LocalBaseManager
from cloudmesh.ai.vm.exceptions import VMProviderError, ConfigError, VMResourceError, VMAuthError, VMNetworkError

class Provider(LocalBaseManager):
    """
    WSL2 implementation of the CloudBaseManager.
    Uses the 'wsl.exe' CLI tool to manage Linux distributions.
    """

    def __init__(self, config: Any, console=None, **kwargs):
        super().__init__(config, console=console, **kwargs)
        self.cloud_name = "wsl2"

    def _get_wsl_binary(self) -> Optional[str]:
        """Return the most portable WSL binary for the current environment."""
        if shutil.which("wsl.exe"):
            return "wsl.exe"
        if shutil.which("wsl"):
            return "wsl"
        return None

    def _normalize_wsl_output(self, output: str) -> str:
        """Normalize Windows-side WSL CLI output when called from WSL."""
        if not output:
            return ""
        if "\x00" in output:
            try:
                # Attempt to decode as UTF-16LE, common for wsl.exe output in some contexts
                decoded = output.encode("utf-8").decode("utf-16le")
                # Basic sanity check: if it's mostly non-printable, it might have been a false positive
                if any(c.isprintable() for c in decoded):
                    return decoded
            except Exception:
                pass
        return output

    def start(self, name: Optional[str] = None, flavor: Optional[str] = None, image: Optional[str] = None, **kwargs) -> str:
        """
        Starts a WSL2 distribution.
        If the distribution doesn't exist, it attempts to import it from a rootfs image.
        """
        if not name:
            raise ConfigError("WSL2 requires a specific distribution name to start.")

        # Check if distro already exists
        if self.exists(name):
            try:
                self._run_command([self._get_wsl_binary(), "-d", name])
                return name
            except Exception as e:
                raise VMProviderError(f"Failed to start existing WSL2 distribution {name}: {e}")

        # Attempt to import if not exists
        cloud_config = self.get_cloud_config("wsl2")
        # Use image override if provided, otherwise fallback to config 'rootfs'
        rootfs = image or cloud_config.get("rootfs")
        install_dir = cloud_config.get("install_dir", "C:\\WSL")

        if not rootfs:
            raise ConfigError(f"Rootfs image path not configured in YAML for wsl2. Cannot import {name}.")

        try:
            # wsl --import <Distro> <InstallLocation> <FileName>
            self._run_command([self._get_wsl_binary(), "--import", name, install_dir, rootfs])
            self._run_command([self._get_wsl_binary(), "-d", name])
            return name
        except Exception as e:
            raise VMProviderError(f"Failed to import and start WSL2 distribution {name}: {e}")

    def stop(self, name: Optional[str] = None) -> bool:
        """
        Stops (terminates) a WSL2 distribution.
        """
        if not name or not self.exists(name):
            raise VMResourceError(f"Distribution {name} not found.")

        try:
            self._run_command([self._get_wsl_binary(), "--terminate", name])
            return True
        except Exception as e:
            raise VMProviderError(f"Failed to stop WSL2 distribution {name}: {e}")

    def delete(self, name: Optional[str] = None) -> bool:
        """
        Deletes (unregisters) a WSL2 distribution.
        """
        if not name or not self.exists(name):
            raise VMResourceError(f"Distribution {name} not found.")

        try:
            self._run_command([self._get_wsl_binary(), "--unregister", name])
            return True
        except Exception as e:
            raise VMProviderError(f"Failed to delete WSL2 distribution {name}: {e}")

    def list(self) -> List[Dict[str, Any]]:
        """
        Lists WSL2 distributions.
        """
        try:
            result = self._run_command([self._get_wsl_binary(), "--list", "--verbose"])
            lines = self._normalize_wsl_output(result.stdout).strip().splitlines()
            if len(lines) < 2:
                return []

            vms = []
            for line in lines[1:]:
                parts = line.split()
                if parts and parts[0] == "*":
                    parts = parts[1:]
                if len(parts) >= 2:
                    vms.append({
                        "name": parts[0],
                        "state": parts[1],
                        "version": parts[2] if len(parts) > 2 else "Unknown"
                    })
            return vms
        except Exception:
            return []

    def login(self, name: Optional[str] = None) -> bool:
        """
        Logs into a WSL2 distribution.
        """
        if not name:
            self.print("Error: Distro name is required to login.")
            return False

        try:
            # launch interactive shell
            self._run_command([self._get_wsl_binary(), "-d", name], stream=True)
            return True
        except Exception:
            return False

    def suspend(self, name: Optional[str] = None) -> bool:
        """
        WSL2 doesn't have a 'suspend' mode; we use terminate.
        """
        return self.stop(name)

    def restart(self, name: Optional[str] = None) -> bool:
        """
        Restarts a WSL2 distribution.
        """
        if not name or not self.exists(name):
            return False
        try:
            self.stop(name)
            self.start(name)
            return True
        except Exception:
            return False

    def get_flavors(self, **kwargs) -> List[Dict[str, Any]]:
        """
        WSL2 does not have 'flavors' in the cloud sense.
        """
        return [{"name": "standard", "description": "Default WSL2 Resource allocation"}]

    def get_keys(self) -> List[Dict[str, Any]]:
        """
        WSL2 uses local user keys.
        """
        return [{"name": "local-user-key", "path": "~/.ssh/id_rsa"}]

    def get_security_groups(self) -> List[Dict[str, Any]]:
        """
        WSL2 uses host firewall/networking.
        """
        return [{"name": "default", "description": "Host network access"}]

    def link_ssh_dir(self, name: Optional[str] = None) -> bool:
        """
        Creates a symbolic link from the WSL2 home .ssh directory
        to the host OS's .ssh directory.
        """
        if not name or not self.exists(name):
            self.print("Error: Valid distro name is required to link SSH directory.")
            return False

        cloud_config = self.get_cloud_config("wsl2")
        wsl_user = cloud_config.get("wsl_username")
        host_user = cloud_config.get("host_username")

        if not wsl_user or not host_user:
            self.print("Error: 'wsl_username' and 'host_username' must be configured in clouds.yaml to link SSH directory.")
            return False

        # Try to determine host SSH path. Default to /mnt/c/Users but allow config override.
        host_base = cloud_config.get("host_ssh_base", "/mnt/c/Users")
        host_ssh_path = f"{host_base}/{host_user}/.ssh"
        wsl_ssh_path = f"/home/{wsl_user}/.ssh"

        try:
            # Use 'ln -sf' to replace existing symlinks, but avoid 'rm -rf' on directories to prevent data loss.
            # First, check if it's a directory and not a link.
            check_cmd = f"[ -d {wsl_ssh_path} ] && [ ! -L {wsl_ssh_path} ] && echo 'exists'"
            check_result = self._run_command([self._get_wsl_binary() or "wsl.exe", "-d", name, "-u", "root", "sh", "-c", check_cmd])

            if "exists" in check_result:
                self.print(f"Warning: {wsl_ssh_path} exists and is a directory. Skipping symlink to prevent data loss.")
                return False

            shell_command = f"ln -sf {host_ssh_path} {wsl_ssh_path}"
            self._run_command([self._get_wsl_binary() or "wsl.exe", "-d", name, "-u", "root", "sh", "-c", shell_command])
            return True
        except Exception:
            return False

    def run_command(self, name: str, cmd: str) -> str:
        """
        Executes a command on the WSL2 distribution.
        """
        if not name or not self.exists(name):
            raise VMProviderError(f"VM {name} not found.")

        cloud_config = self.get_cloud_config("wsl2")
        wsl_user = cloud_config.get("wsl_username", "root")

        try:
            result = self._run_command([self._get_wsl_binary(), "-d", name, "-u", wsl_user, "sh", "-c", cmd])
            return result.stdout
        except Exception as e:
            return f"Error executing command: {e}"

    def info(self, name: str) -> Dict[str, Any]:
        """Gets detailed information about a WSL2 distribution."""
        if not name or not self.exists(name):
            raise VMResourceError(f"Distribution {name} not found")

        # Reuse list() to get the distributions and their states.
        vms = self.list()
        for vm in vms:
            if vm["name"] == name:
                return {"Name": vm["name"], "State": vm["state"], "Version": vm["version"]}

        raise VMResourceError(f"Distribution {name} not found in list")

    @property
    def version(self) -> List[str]:
        """
        Returns a list of version strings for the WSL tool.
        """
        try:
            result = self._run_command([self._get_wsl_binary(), "--version"])
            output = self._normalize_wsl_output(result.stdout)
            lines = output.strip().split("\n")
            return [line.strip() for line in lines if ":" in line]
        except Exception:
            pass
        return ["Unknown"]

    def check_requirements(self) -> bool:
        """
        Checks if the requirements for this provider are met on the current system.
        """
        # Use our portable binary detection to see if any WSL executable is available.
        # This allows the provider to be detected even when running from inside WSL.
        binary = self._get_wsl_binary()
        import shutil
        return shutil.which(binary) is not None

    def _get_current_status(self, name: str) -> str:
        """Returns the current status of the WSL2 distribution."""
        vms = self.list()
        vm = next((v for v in vms if v["name"] == name), None)
        return vm["state"] if vm else ""

    def validate_config(self) -> Dict[str, List[str]]:
        """
        Validates WSL2 configuration.
        """
        errors_map = {}
        config = self.get_cloud_config("wsl2")

        config_name = "Cloudmesh config (~/.config/cloudmesh/clouds.yaml)"
        errors = []
        if not config.get("rootfs"):
            errors.append("Missing required field: 'rootfs' (rootfs image path)")

        if errors:
            errors_map[config_name] = errors

        return errors_map

    def get_provider_info(self) -> Dict[str, Any]:
        """Gets detailed information about the WSL2 provider."""
        return {
            "provider": "WSL2",
            "cloud_name": self.cloud_name,
            "version": self.version,
            "config": {
                "install_dir": self.get_cloud_config("wsl2").get("install_dir", "C:\\WSL"),
            },
        }

