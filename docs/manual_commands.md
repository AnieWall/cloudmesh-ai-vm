# VM Commands (Collapsible Index)

This page provides a **collapsible overview** of all `cmx vm` commands.  Each section expands to show a short description of the sub‑commands and a link to the full documentation (the main manual page).

<details>
<summary>Configuration (`cmx vm config`)</summary>

- `get KEY` – Get a specific configuration value.
- `init` – Initialize the VM CLI configuration.
- `list` – List all current VM configuration settings.
- `set KEY VALUE` – Set a configuration value.

[Full documentation](manual.md#configuration-cmx-vm-config)
</details>

<details>
<summary>Lifecycle Management</summary>

- `start [NAME]` – Starts or launches a VM.
  - Options: `--count <int>`, `--range <range>`, `--noip`.
- `stop [NAME]` – Stops a running VM.
- `restart [NAME]` – Restarts a VM.
- `suspend [NAME]` – Suspends a VM to disk.
- `shelve [NAME]` – Shelve the VM (OpenStack only).
- `unshelve [NAME]` – Unshelve the VM (OpenStack only).
- `delete [NAME]` – Deletes a VM from the provider.
- `reset [NAME]` – Reset a VM or restart the provider service.

[Full documentation](manual.md#lifecycle-management)
</details>

<details>
<summary>Resource Discovery</summary>

- `list` – List VM resources (e.g., `vms`, `regions`).
  - Options: `--all` to list resources from all enabled providers.
- `info NAME` – Get detailed information about a specific VM.
- `image` – List available VM images for the active provider.
- `flavor` – List available VM flavors/sizes.
- `security-group` – Manage firewall security groups (sub‑commands: `list`, `info`, `create`, `delete`, `add`, `remove`, `rule`).

[Full documentation](manual.md#resource-discovery)
</details>

<details>
<summary>Provider Management (`cmx vm provider`)</summary>

- `get` – Get the current default cloud provider.
- `set PROVIDER` – Set the default cloud provider.
- `list` – List all supported providers and their configuration status.
- `info` – Display detailed information about the active provider.

[Full documentation](manual.md#provider-management-cmx-vm-provider)
</details>

<details>
<summary>Key Management (`cmx key`)</summary>

- `upload KEY_PATH` – Upload a public SSH key to the cloud provider (optional `--name`).
- `list` – List all SSH keys for the current provider.
- `delete KEY_NAME` – Delete an SSH key from the provider.

[Full documentation](manual.md#key-management-cmx-key)
</details>

<details>
<summary>VM Interaction & Utilities</summary>

- `run [NAME] [COMMAND]` – Execute a command on a VM via SSH.
- `ssh [NAME]` – Start an interactive SSH session with the VM.
- `login [NAME]` – Get connection info or log into the VM.
- `ssh-config [NAME]` – Generate a local SSH configuration snippet.

[Full documentation](manual.md#vm-interaction-utilities)
</details>

<details>
<summary>Account & System</summary>

- `account` – View account information, usage quotas, and limits.
- `horizon` – Open the OpenStack Horizon dashboard in the default browser.
- `reset` – Restart the cloud provider service or reset the local environment.
- `status` – Show a summary of the current state of the selected cloud (or all clouds).  **(Also available as a dedicated page: [VM Status](vm_status.md)).**
- `purge` – Delete all VMs, floating IPs, and reservations for a cloud.  **(Also available as a dedicated page: [VM Purge](vm_purge.md)).**

[Full documentation](manual.md#account-system)
</details>

*Use the dropdown arrows to expand each section and see the available sub‑commands.*
