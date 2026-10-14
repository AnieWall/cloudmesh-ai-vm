# SSH Key Management Specification

This document summarizes the functionality of the `cmx vm key` command group used for managing SSH keys within the Cloudmesh AI VM environment.

## Commands

### `cmx vm key scan`
Scans the local host machine for existing SSH keys.
- **Functionality**: Identifies local SSH keys and displays their properties in a table.
- **Output**: 
  - Path to the key
  - Key type
  - Fingerprint (SHA256)
  - Fingerprint (MD5)
  - Comment
  - Passphrase status (Yes/No)
- **Note**: Displays a security warning advising users not to use these local keys for cloud providers (e.g., AWS, Azure, Google) and recommending the use of dedicated keys.

### `cmx vm key github`
A command group for managing SSH keys specifically for GitHub.

#### `cmx vm key github list`
Lists the SSH keys currently configured on the user's GitHub account.
- **Output**: Table containing the Name, Fingerprint, and Type of each key.
- **Format**: Supports JSON output via the `--json` flag.

#### `cmx vm key github upload <key_path>`
Uploads a specified local public key to the user's GitHub account.
- **Argument**: `key_path` - The path to the local public key file to be uploaded.

#### `cmx vm key github verify`
Checks which of the local SSH keys are registered and authenticated with GitHub.
- **Functionality**: Scans local keys and verifies their authentication status against GitHub.
- **Output**: Table containing:
  - Local path to the key
  - Authentication status (Yes/No)
  - GitHub key name
  - Fingerprint
  - Creation date
  - Last used date
- **Format**: Supports JSON output via the `--json` flag.
