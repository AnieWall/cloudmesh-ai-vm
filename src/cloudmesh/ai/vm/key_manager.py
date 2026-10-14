import os
import subprocess
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger("cloudmesh.ai.vm")

class KeyManager:
    """
    Utility class for managing SSH keys and GitHub integration.
    """

    COMMON_KEY_NAMES = ["id_ed25519", "id_rsa", "id_ecdsa", "id_dsa"]

    def __init__(self):
        self.ssh_dir = Path.home() / ".ssh"

    def scan_local_keys(self) -> List[Dict[str, Any]]:
        """
        Scans the ~/.ssh directory for common private keys and checks for passphrases.
        """
        keys = []
        if not self.ssh_dir.exists():
            logger.warning(f"SSH directory not found: {self.ssh_dir}")
            return keys

        for file in self.ssh_dir.iterdir():
            # A file is considered a private key if:
            # 1. It starts with a common key name (id_rsa, etc.)
            # 2. OR it has a .pem extension
            # 3. AND it is not a public key (.pub)
            is_common_name = any(file.name.startswith(name) for name in self.COMMON_KEY_NAMES)
            is_pem = file.suffix == ".pem"

            if (is_common_name or is_pem) and file.suffix != ".pub":
                key_type = self._get_key_type(file)
                has_passphrase = self._has_passphrase(file)
                keys.append({
                    "path": str(file),
                    "type": key_type,
                    "has_passphrase": has_passphrase
                })

        return keys

    def _get_key_type(self, key_path: Path) -> str:
        """
        Attempts to determine the key type from the file content or name.
        """
        try:
            with open(key_path, 'r') as f:
                first_line = f.readline().strip()
                if "OPENSSH PRIVATE KEY" in first_line:
                    if "ed25519" in key_path.name: return "ed25519"
                    if "rsa" in key_path.name: return "rsa"
                    if "ecdsa" in key_path.name: return "ecdsa"
                    if "dsa" in key_path.name: return "dsa"
                    return "openssh"
                if "RSA PRIVATE KEY" in first_line: return "rsa"
                if "DSA PRIVATE KEY" in first_line: return "dsa"
                if "EC PRIVATE KEY" in first_line: return "ecdsa"
                if "PRIVATE KEY" in first_line:
                    # PKCS#8 format - type is not in the header. Try filename.
                    if "ed25519" in key_path.name: return "ed25519"
                    if "rsa" in key_path.name: return "rsa"
                    if "ecdsa" in key_path.name: return "ecdsa"
                    if "dsa" in key_path.name: return "dsa"
                    return "pkcs8"
        except Exception:
            pass

        # Final fallback: check filename for any key-like file
        name = key_path.name.lower()
        if "ed25519" in name: return "ed25519"
        if "rsa" in name: return "rsa"
        if "ecdsa" in name: return "ecdsa"
        if "dsa" in name: return "dsa"

        return "unknown"

    def _has_passphrase(self, key_path: Path) -> bool:
        """
        Checks if a private key is protected by a passphrase.
        """
        try:
            # ssh-keygen -y -f <key> tries to read the public key from the private key.
            # If it's encrypted, it will fail or prompt for a passphrase.
            # In BatchMode, it should fail immediately if a passphrase is required.
            result = subprocess.run(
                ["ssh-keygen", "-y", "-f", str(key_path)],
                capture_output=True,
                text=True,
                timeout=5,
                stdin=subprocess.DEVNULL
            )
            # If ssh-keygen fails and the output mentions a passphrase, it's encrypted.
            # Or if it just fails in a way that suggests it needs a password.
            if result.returncode != 0:
                return True
            return False
        except Exception as e:
            logger.debug(f"Error checking passphrase for {key_path}: {e}")
            return False

    def verify_github_auth(self, key_path: str) -> bool:
        """
        Verifies if a specific SSH key authenticates successfully with GitHub.
        """
        try:
            # BatchMode=yes prevents interactive prompts
            # ConnectTimeout prevents hanging
            result = subprocess.run(
                ["ssh", "-i", key_path, "-o", "BatchMode=yes", "-o", "ConnectTimeout=5", "git@github.com"],
                capture_output=True,
                text=True,
                timeout=10
            )
            # GitHub typically returns "Hi [username]!" on successful auth
            return result.returncode == 0 or "Hi" in result.stdout or "Hi" in result.stderr
        except Exception as e:
            logger.debug(f"Error verifying GitHub auth for {key_path}: {e}")
            return False

    def github_upload(self, key_path: str) -> Dict[str, Any]:
        """
        Uploads a local SSH key to GitHub using the gh CLI.
        """
        private_key_path = Path(key_path)
        # Try to find the corresponding public key (.pub)
        public_key_path = private_key_path.with_suffix(private_key_path.suffix + ".pub")
        if not public_key_path.exists():
            # If .pub doesn't exist, try to generate it from the private key
            try:
                pub_out = subprocess.run(
                    ["ssh-keygen", "-y", "-f", str(private_key_path)],
                    capture_output=True,
                    text=True,
                    check=True
                )
                # Write it to a temporary file or just pass it if gh supports it.
                # gh ssh-key add requires a path to a file.
                temp_pub = public_key_path
                with open(temp_pub, "w") as f:
                    f.write(pub_out.stdout)
            except subprocess.CalledProcessError as e:
                return {"success": False, "error": f"Could not generate public key: {e.stderr}"}
        else:
            public_key_path = public_key_path

        try:
            result = subprocess.run(
                ["gh", "ssh-key", "add", str(public_key_path)],
                capture_output=True,
                text=True,
                check=True
            )
            return {"success": True, "output": result.stdout}
        except subprocess.CalledProcessError as e:
            return {"success": False, "error": e.stderr or e.stdout}
        except FileNotFoundError:
            return {"success": False, "error": "GitHub CLI ('gh') not found. Please install it."}

    def github_list(self) -> List[Dict[str, Any]]:
        """
        Lists the SSH keys currently configured in GitHub.
        """
        try:
            result = subprocess.run(
                ["gh", "ssh-key", "list"],
                capture_output=True,
                text=True,
                check=True
            )
            # gh ssh-key list output is usually a table.
            # We can try to parse it or just return the raw output.
            # For a proper table, we'd need to parse the lines.
            lines = result.stdout.strip().split('\n')
            if not lines:
                return []

            # Simple parsing of gh ssh-key list output
            # Expected format: NAME | FINGERPRINT | KEY_TYPE
            keys = []
            headers = lines[0].split()
            for line in lines[1:]:
                parts = line.split()
                if len(parts) >= 2:
                    keys.append({
                        "name": parts[0],
                        "fingerprint": parts[1],
                        "type": parts[2] if len(parts) > 2 else "unknown"
                    })
            return keys
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to list GitHub keys: {e.stderr}")
            return []
        except FileNotFoundError:
            logger.error("GitHub CLI ('gh') not found.")
            return []
