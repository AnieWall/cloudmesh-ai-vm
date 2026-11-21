# cmx vm provider

## Overview

5 | Manage the cloud providers available to the tool.
6 |
7 | **Provider Selection Precedence**
8 | The active cloud provider is resolved using the following order (first match wins):
9 | 1. CLI `--cloud` flag (temporary override for a single command).
10 | 2. `OS_CLOUD` environment variable (overrides the default configured cloud).
11 | 3. `default_cloud` entry in `~/.config/cloudmesh/clouds.yaml`.
12 | 4. Fallback to `multipass` if none of the above are set.

### Sub‑commands

- `get` – Get the current default cloud provider.
- `set PROVIDER` – Set the default cloud provider.
- `list` – List all supported providers and their configuration status.
- `info` – Display detailed information about the active provider.
  - For the **WSL2 provider**, the tool automatically detects the best available binary (`wsl.exe` or `wsl`).

## Usage

```bash
cmx vm provider <subcommand> [options]
```
