# cloudmesh-ai-vm

`cloudmesh-ai-vm` is a unified Python CLI tool (`cmx`) that simplifies the deployment and management of Virtual Machines (VMs) across a diverse ecosystem of providers. By providing a single, consistent interface, it abstracts the complexities of different cloud APIs, allowing users to focus on their workloads rather than the underlying infrastructure.

## Key Features

- **Unified Interface**: Manage local virtualization (Multipass, WSL2, VirtualBox, Lima) and public clouds (OpenStack, AWS, Azure, GCP, Oracle) using one consistent CLI.
- **Smart VM Lifecycle**:
    - **Automatic Naming**: VMs are named automatically using a `<username>-<counter>` pattern (e.g., `gregor-1`), eliminating the need to invent unique names for every instance.
    - **Contextual Memory**: The tool remembers the last used VM, allowing you to run commands like `cmx vm stop` without specifying a name.
- **Provider Flexibility**:
    - **Default Cloud**: Set your active provider via `cmx vm provider set <cloud>`.
    - **Cloud Override**: Use the `--cloud` flag to temporarily target a different provider (e.g., `cmx vm start --cloud aws`).
- **Remote Execution**: Execute commands directly on your VMs via SSH using `cmx vm run <command>`, bypassing the need for manual SSH login for simple tasks.
- **Integrated SSH Key Management**: Scan for local keys, verify GitHub authentication, and upload public keys to cloud providers directly from the CLI.
- **Security Management**: Create, assign, and manage firewall rules with smart-presets for common server roles (e.g., web, database).
- **SSH Integration**: Automatically generate suggested SSH configuration entries for existing VMs to enable seamless access via `ssh <hostname>`.
- **Interactive Shell**: Enter a dedicated VM management shell using `cmx vm -i` for faster iterative workflows.
- **SDK-Native Implementations**: High-stability providers (like Chameleon and Jetstream) are implemented using official SDKs for maximum feature support.

The full documentation is available at: <https://cloudmesh-ai.github.io/cloudmesh-ai-vm/>

## Quick Start

### 1. Installation

```bash
git clone https://github.com/cloudmesh/cloudmesh-ai-vm.git
cd cloudmesh-ai-vm
pip install -e .
```

### 2. Configuration

Configure your credentials in `~/.config/cloudmesh/clouds.yaml`. See the [Configuration Guide](docs/configuration.md) for details.

### 3. Basic Usage

```bash
# Set your default cloud (e.g., multipass, aws, openstack)
cmx vm provider set multipass

# Start a VM (automatically named username-1, username-2, etc.)
cmx vm start

# Run a command on the VM
cmx vm run "hostname"

# Log into the VM (interactive)
cmx vm login

# Stop the last started VM
cmx vm stop

# Start a VM on a specific cloud (override default)
cmx vm start --cloud aws

# List all VMs for current cloud
cmx vm list

# Upload your default public key (~/.ssh/id_rsa.pub) to the cloud
cmx key upload

# Enter interactive VM shell
cmx vm -i
```

## Provider Support Matrix

| Provider | Lifecycle (S/S/D) | Remote Exec (`run`) | Implementation Status |
| :--- | :---: | :---: | :--- |
| **Multipass** | ✅ | ✅ (Agent) | 🟢 |
| **Lima** | ✅ | ✅ (Agent) | 🟢 |
| **OpenStack** | ✅ | ✅ (SSH) | 🟢 (via Libcloud/SDK) |
| **WSL2** | ✅ | ✅ (Direct) | 🟢 |
| **VirtualBox** | ✅ | ✅ (GuestCtrl) | 🟢 |
| **AWS** | ✅ | ✅ (SSH) | 🟢 (via Libcloud) |
| **Azure** | ✅ | ✅ (SSH) | 🟢 (via Libcloud) |
| **Google** | ✅ | ✅ (SSH) | 🟢 (via Libcloud) |
| **Oracle** | ✅ | ✅ (SSH) | 🟢 (via Libcloud) |

🟡 = has been implemented but not tested. We anticipate issues

## Documentation

Full documentation is available in the `/docs` folder or hosted via GitHub Pages.

- [Installation Guide](docs/installation.md)
- [Configuration Guide](docs/configuration.md)
- [CLI Reference](docs/cli.md)
- [Architecture Overview](docs/architecture.md)

## Testing

The project uses a tiered testing strategy to ensure stability across multiple cloud and local providers:

### Testing Structure

- `tests/unit`: **Unit Tests**. High-isolation tests that use mocks to verify internal logic and CLI behavior without requiring external infrastructure.
- `tests/integration`: **Integration Tests**. End-to-end tests that perform real operations against actual cloud infrastructure.
- `tests/compliance`: **Compliance Suite**. Ensures every provider implements a consistent interface and meets the minimum functional baseline. Includes "Scenario Tests" for end-to-end user flows.
- `tests/smoke`: **Smoke Tests**. Quick, high-level checks to verify that the CLI and providers load and execute basic commands without crashing.
- `tests/bin`: Utility scripts and helper binaries used by the test suite.

### Running Compliance Tests

Tests can be run in two modes:


- **Unit Mode (Default)**: Uses a standardized `MockDriver` to verify return types and basic logic without needing cloud credentials, ensuring a reliable functional baseline across all providers.
  ```bash
  PYTHONPATH=. pytest tests/compliance/test_compliance.py
  ```

- **Integration Mode**: Performs real operations against actual cloud infrastructure. Requires valid credentials in your configuration.
  ```bash
  PYTHONPATH=. COMPLIANCE_MODE=integration pytest tests/compliance/test_compliance.py
  ```

The compliance suite also includes **Scenario Tests** (such as the "Zero-to-Hero" flow) to validate that the end-to-end user experience—from configuration validation to VM deletion—is consistent across all supported cloud and local providers.

## Contributing

See [Contributing](docs/contributing.md) for guidelines on adding new providers.

**Note**: To be added to the `CONTRIBUTORS.md` file, please submit a separate Pull Request specifically for that purpose.

---