import logging
import subprocess
from abc import ABC

from .CloudBaseManager import CloudBaseManager
from .exceptions import ProviderFeatureNotSupported

logger = logging.getLogger("cloudmesh.ai.vm")


class LocalBaseManager(CloudBaseManager, ABC):
    """
    Base class for local VM providers (Multipass, VBox, WSL2, Lima).
    Standardizes CLI execution and common local VM operations.
    """

    def _run_command(
        self, command: list[str], stream: bool = False
    ) -> subprocess.CompletedProcess:
        """
        Unified helper to run shell commands.

        Args:
            command: The command to execute as a list.
            stream: If True, prints output to the console in real-time.
        """
        try:
            if stream:
                process = subprocess.Popen(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                )
                full_output = []
                for line in process.stdout:
                    self.print_ansi(line, end="")
                    full_output.append(line)
                process.wait()

                if process.returncode != 0:
                    raise subprocess.CalledProcessError(
                        process.returncode,
                        command,
                        output="".join(full_output),
                        stderr="".join(full_output),
                    )
                return subprocess.CompletedProcess(
                    args=command,
                    returncode=process.returncode,
                    stdout="".join(full_output),
                    stderr=None,
                )
            else:
                return subprocess.run(
                    command, capture_output=True, text=True, check=True
                )
        except subprocess.CalledProcessError as e:
            logger.error(f"CLI command failed: {' '.join(command)} - {e.stderr}")
            raise e
        except Exception as e:
            logger.error(f"Unexpected error executing command {' '.join(command)}: {e}")
            raise e

    # ---------------------------------------------------------------------
    # CLI helper with secret‑masking
    # ---------------------------------------------------------------------
    def _run_cli_and_mask(self, *args, **kwargs):
        """Execute a CLI command via ``_run_command`` while ensuring that any
        exception message is stripped of credential‑like patterns.

        This method mirrors the behaviour that ``OpenstackManager`` previously
        implemented in its private ``_run_cli_command`` helper, but lives in the
        base class so that *any* provider that needs to invoke an external CLI can
        benefit from the same sanitisation logic.
        """
        from cloudmesh.ai.command._shared.providers_utils import sanitize_output
        from cloudmesh.ai.vm.exceptions import VMProviderError

        try:
            result = self._run_command(*args, **kwargs)
            # ``_run_command`` raises on non‑zero exit codes, but when mocked it
            # can return an object with a ``returncode`` attribute. Guard against
            # that scenario as well.
            if hasattr(result, "returncode") and result.returncode != 0:
                raise VMProviderError("CLI command failed")
            return result
        except Exception as e:
            # Remove any secret fragments before propagating the error.
            safe_msg = sanitize_output(str(e))
            raise VMProviderError(f"CLI command failed: {safe_msg}") from e

    def exists(self, name: str) -> bool:
        """
        Checks if a VM exists by searching the list of all VMs.
        """
        vms = self.list()
        if not vms:
            return False

        # Local providers might use 'Name' or 'name' as the key
        for vm in vms:
            if vm.get("Name") == name or vm.get("name") == name:
                return True
        return False

    def upload_key(
        self, key_path: str, key_name: str, vm_name: str | None = None
    ) -> bool:
        """
        Uploads a public key to the local VM.
        Implementation: Appends the key to ~/.ssh/authorized_keys via run_command.
        """
        # This requires the VM to be running and accessible via run_command
        # Since we don't have a VM name here, this is typically called
        # in a context where we know which VM we are targeting.
        # For the base class, we raise NotSupported as it needs a VM target.
        raise ProviderFeatureNotSupported(self.cloud_name, "upload_key")

    def delete_key(self, key_name: str, vm_name: str | None = None) -> bool:
        """
        Deletes a public key from the local VM.
        """
        raise ProviderFeatureNotSupported(self.cloud_name, "delete_key")
