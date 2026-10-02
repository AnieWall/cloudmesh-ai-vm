# Provider Compliance Guide

This guide outlines the "Provider Contract" for the `cloudmesh-ai-vm` framework. To ensure a consistent user experience across different cloud and local providers, every provider manager must implement a specific set of methods and adhere to a standardized data format.

## 1. The Provider Contract

All providers must inherit from `BaseVMProvider` (or `CloudBaseManager` / `LocalBaseManager`). A provider is considered **Compliant** when it implements the following interfaces without crashing, even when provided with incomplete configurations (by handling errors gracefully).

### 1.1 Mandatory Core Methods (The Baseline)
These methods are tested by the compliance suite. Failure in any of these is considered a critical bug.

| Method | Purpose | Expected Return Value |
| :--- | :--- | :--- |
| `validate_config()` | Checks if required credentials/settings are present. | `Dict[str, List[str]]` (Key: config section, Value: list of error strings). Return `{}` if valid. |
| `exists(name)` | Verifies if a VM with the given name exists. | `bool` |
| `list()` | Lists all available VMs in the provider. | `List[Dict[str, Any]]`. Each dict must contain at least `{"name": str, "status": str, "ip": str}`. |
| `info(name)` | Gets detailed metadata for a specific VM. | `Dict[str, Any]`. Must return a dict with VM details or a dict containing `{"error": str}`. |
| `get_provider_info()`| Returns metadata about the provider itself. | `Dict[str, Any]`. Should include `provider`, `cloud_name`, and `version`. |

### 1.2 Lifecycle Methods
Implement these to support the `cmx vm start/stop/delete` commands.

| Method | Expected Behavior | Return Value |
| :--- | :--- | :--- |
| `start(...)` | Launches a VM. Should handle image/flavor resolution. | `str` (The VM ID or Name) |
| `stop(name)` | Gracefully stops or terminates a VM. | `bool` (True if successful) |
| `delete(name)` | Permanently removes the VM. | `bool` (True if successful) |
| `restart(name)` | Reboots the VM. | `bool` (True if successful) |
| `wait_for_status(...)`| Polls the VM state until it matches `target_status`. | `bool` (True if reached within timeout) |

### 1.3 Identity & Security Methods
| Method | Purpose | Return Value |
| :--- | :--- | :--- |
| `get_keys()` | Lists SSH keys available in the cloud. | `List[Dict[str, Any]]` |
| `upload_key(...)` | Uploads a public key to the provider. | `bool` |
| `delete_key(...)` | Removes a public key from the provider. | `bool` |
| `get_security_groups()`| Lists available firewall/security groups. | `List[Dict[str, Any]]` |

---

## 2. How to Implement a New Provider

### Step 1: Choose the Base Class
- **Hyperscalers (AWS, Azure, GCP, OpenStack)**: Inherit from `LibcloudManager`. This gives you a standardized wrapper around the `apache-libcloud` library.
- **Local Providers (Multipass, VBox, WSL2)**: Inherit from `LocalBaseManager`. This provides a unified `_run_command` helper for CLI-based management.
- **Custom SDKs (Oracle)**: Inherit from `CloudBaseManager` and implement your own driver initialization.

### Step 2: Implement `_get_driver` (for Libcloud)
If using `LibcloudManager`, you must implement `_get_driver()`. This method should:
1. Retrieve credentials via `self.get_cloud_config()`.
2. Return an instance of the corresponding `libcloud` driver.

### Step 3: Handle Exceptions
Do **not** let providers crash during `__init__`. If credentials are missing:
- Log a warning.
- Ensure methods like `validate_config()` can still run.
- Use `ProviderFeatureNotSupported` when a method is called but the provider doesn't support it.

### Step 4: Verify with the Compliance Suite
Once implemented, add your provider to `src/cloudmesh/ai/vm/providers/__init__.py` (or the `PROVIDER_MAP`) and run the compliance tests:

```bash
# Run unit tests (mocked drivers)
pytest tests/compliance/test_compliance.py

# Run integration tests (requires real credentials in clouds.yaml)
COMPLIANCE_MODE=integration pytest tests/compliance/test_compliance.py
```

## 3. Common Pitfalls
- **Case Sensitivity**: Ensure VM names are handled case-insensitively where the provider allows.
- **Status Normalization**: Different providers use different terms for "Running" (e.g., `ACTIVE` in OpenStack, `running` in Multipass). Always `.lower()` your status checks.
- **Blocking Calls**: Use `wait_for_status` when an operation (like `start`) is asynchronous to prevent the CLI from returning before the VM is actually ready.
