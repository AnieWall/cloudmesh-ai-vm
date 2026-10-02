# Changelog

## [1.4.0] - 2026-10-01

### Added
- **Provider Compliance Suite**: Implemented a standardized testing framework to ensure all VM providers meet a minimum functional baseline, featuring core mandatory tests and optional feature checks.
- **Lifecycle Parity**: Implemented `restart`, `reset`, and `suspend` for all cloud-based providers (AWS, Azure, Google, Oracle).
- **Network Feature Parity**: Implemented `assign_floating_ip` and `release_floating_ip` for AWS, Azure, and Google providers via `LibcloudManager`.
- **Existence Checks**: Implemented `exists()` method across all providers to verify VM presence before performing operations, eliminating noisy stack traces and crashes.
- **Local Provider Base Class**: Introduced `LocalBaseManager` to centralize CLI execution logic for Multipass, VBox, WSL2, and Lima, supporting both silent and streaming output.
- **Compliance Integration Mode**: Added `COMPLIANCE_MODE` environment variable to the provider compliance suite, allowing tests to run in `unit` (mocked) or `integration` (real infrastructure) mode.
- **MockDriver Infrastructure**: Implemented a `MockDriver` factory for the compliance suite. Instead of falling back to a generic `MagicMock` when a provider crashes during `__init__`, the suite now patches `_get_driver` (or `_init_oci_client`) to return a structured `MockDriver`, ensuring "Core" tests return correct types (e.g., `dict` for config validation) and pass reliably.
- **UX Scenario Testing**: Added "Zero-to-Hero" flow tests to the compliance suite to ensure consistent end-to-end behavior across all providers.
- **State Polling**: Implemented `wait_for_status()` across all VM providers to allow the CLI to wait for VMs to reach a specific state (e.g., RUNNING), preventing race conditions during lifecycle operations.
- **Provider Metadata**: Implemented `get_provider_info()` for all managers, enabling the `cmx vm provider get` command to return detailed version and status information.

### Changed
- **Exception Handling**: Began standardizing exception handling by replacing generic `ValueError` and `RuntimeError` with specific `ConfigError` and `VMResourceError` in `LibcloudManager`.
- **Libcloud Consolidation**: Moved redundant `start()` and `version` implementations from `AwsManager`, `AzureManager`, and `GoogleManager` into `LibcloudManager` to reduce code duplication.
- **SSH Execution**: Unified SSH command execution by extracting a shared `_execute_ssh_command` helper into `CloudBaseManager`, reused by both libcloud and OCI providers.
- **Local Providers**: Migrated Multipass, VBox, WSL2, and Lima managers to inherit from `LocalBaseManager`, removing boilerplate `_run_command` implementations.
- **Stability**: Updated `stop()`, `delete()`, and `info()` methods across all providers to utilize the new `exists()` check for cleaner error reporting.

## [1.3.0] - 2026-09-18

### Added
- **New CLI Command**: Implemented `cmc vm image` to list available images for the active cloud provider.
- **Cloud Defaults**: Added recommended default images, flavors, and regions for Jetstream and Chameleon Cloud in sample and local configurations.
- **VM Information**: Introduced `info()` method to retrieve detailed VM metadata (ID, State, IPs, RAM, CPUs) across all providers.
- **Provider Validation**: Added `check_requirements()` to unify how the CLI detects if a provider is supported on the current host system.
- **Command Execution**: Added `run_command()` abstract method to the provider interface for remote command execution.

### Fixed
- **OpenStack Resource Visibility**: Resolved an issue where `apache-libcloud` returned empty lists for non-public images and flavors; implemented a robust fallback to the `openstack` CLI for these resources.

### Changed
- **Provider Table**: Changed the "Enabled" status indicator from a yellow dot to a white dot for providers with missing configuration.
- **CLI Output**: Removed debug messages from `cmc vm provider`.
- **OpenStack Driver**: Enhanced `OpenstackManager` to dynamically retrieve and apply the `region` from `~/.config/openstack/clouds.yaml`.
- **Libcloud Initialization**: Modified `LibcloudManager` to avoid hard failures during driver initialization when performing requirement checks.

# Changelog

## [1.2.1] - 2026-09-18

### Fixed
- **Configuration Access**: Resolved a systemic bug where VM managers failed to handle both `dict` and `GlobalConfig` objects; implemented `get_cloud_config` helper in `CloudBaseManager` to unify access.
- **Test Robustness**:
    - Fixed `MagicMock` leakage in `LimaManager` tests that caused incorrect command string assertions.
    - Resolved `test_hello` failure by implementing the missing `hello` CLI command.
    - Corrected exception type expectations in `LibcloudManager` tests.
    - Added pre-start cleanup to Multipass smoke tests to prevent failures when VMs already exist.

### Changed
- **Test Architecture**: Reorganized tests into `tests/unit` and `tests/smoke` directories to separate fast unit tests from slow, environment-dependent smoke tests.

## [1.2.0] - 2026-09-18

## [1.1.0] - 2026-09-18

### Added
- **Engineering Robustness**: Implemented a structured custom exception hierarchy (`CloudMeshError` $\rightarrow$ `ProviderError`) and a centralized logging framework to replace generic print statements.
- **Comprehensive Documentation**: Established an extensible documentation system using MkDocs and the Material theme.
    - Detailed guides for Local, OpenStack, and Hyperscaler providers.
    - Full CLI reference with usage examples.
    - Architecture overview explaining the Provider Pattern.
- **CI/CD Automation**: Added GitHub Actions workflow for automatic publishing of documentation to GitHub Pages.
- **Documentation Infrastructure**: Created `requirements-docs.txt` and `mkdocs.yml` aligned with Cloudmesh AI organizational standards.

### Changed
- **LibcloudManager**: Refactored to use the new logging system and custom exception hierarchy for better error reporting.

## [1.0.0] - 2026-09-18

### Added
- **Core Architecture**: Implemented Provider Pattern using `CloudBaseManager` (ABC) to unify VM management across multiple providers.
- **Local Providers**:
    - `MultipassManager`: Full lifecycle support with custom resource configuration.
    - `Wsl2Manager`: Support for distribution management and SSH key linking.
    - `VBoxManager`: Headless VM management via `VBoxManage`.
- **OpenStack Providers**:
    - `OpenstackManager`: Base class for OpenStack operations using `libcloud`.
    - `JetstreamManager`: Implementation for Jetstream cloud.
    - `ChameleonManager`: Implementation for Chameleon Cloud, including a specialized `reservation` (lease) system via `python-chi`.
- **Hyperscaler Providers**:
    - `LibcloudManager`: Generic base for libcloud-supported hyperscalers.
    - `AwsManager`: Integration for Amazon EC2.
    - `AzureManager`: Integration for Azure VMs.
    - `GoogleManager`: Integration for Google Compute Engine.
- **CLI Tool**: Developed the `cmc` command-line interface using `click`.
    - `cmc vm set`: Change default cloud provider.
    - `cmc vm start`: Launch a VM with automatic naming.
    - `cmc vm stop/delete/suspend/restart`: VM lifecycle management.
    - `cmc vm list`: List VMs in Table, JSON, YAML, or CSV formats.
    - `cmc vm login`: Connect to VMs.
    - `cmc vm reservation`: Hardware lease management for Chameleon Cloud (supports explicit dates or `--duration`).
- **Testing**: Created comprehensive `pytest` suites for all providers using `unittest.mock`.

### Changed
- Updated `README.md` to document new providers, configuration options, and CLI usage.

### Fixed
- Resolved syntax errors in `LibcloudManager` related to method implementation and abstract class requirements.