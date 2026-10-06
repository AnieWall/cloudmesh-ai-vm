import subprocess
import logging
from abc import ABC
from typing import List, Dict, Any, Optional
from .CloudBaseManager import CloudBaseManager
from .exceptions import VMProviderError, ProviderFeatureNotSupported

logger = logging.getLogger("cloudmesh.ai.vm")

class LocalBaseManager(CloudBaseManager, ABC):
    """
    Base class for local VM providers (Multipass, VBox, WSL2, Lima).
    Standardizes CLI execution and common local VM operations.
    """

    def _run_command(self, command: List[str], stream: bool = False) -> subprocess.CompletedProcess:
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
                    bufsize=1
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
                        stderr="".join(full_output)
                    )
                return subprocess.CompletedProcess(
                    args=command, 
                    returncode=process.returncode, 
                    stdout="".join(full_output), 
                    stderr=None
                )
            else:
                return subprocess.run(command, capture_output=True, text=True, check=True)
        except subprocess.CalledProcessError as e:
            logger.error(f"CLI command failed: {' '.join(command)} - {e.stderr}")
            raise e
        except Exception as e:
            logger.error(f"Unexpected error executing command {' '.join(command)}: {e}")
            raise e

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

    def upload_key(self, key_path: str, key_name: str, vm_name: Optional[str] = None) -> bool:
        """
        Uploads a public key to the local VM.
        Implementation: Appends the key to ~/.ssh/authorized_keys via run_command.
        """
        # This requires the VM to be running and accessible via run_command
        # Since we don't have a VM name here, this is typically called
        # in a context where we know which VM we are targeting.
        # For the base class, we raise NotSupported as it needs a VM target.
        raise ProviderFeatureNotSupported(self.cloud_name, "upload_key")

    def delete_key(self, key_name: str, vm_name: Optional[str] = None) -> bool:
        """
        Deletes a public key from the local VM.
        """
        raise ProviderFeatureNotSupported(self.cloud_name, "delete_key")
