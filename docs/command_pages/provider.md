# cmx vm provider

## Overview

Manage the cloud providers available to the tool.

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
