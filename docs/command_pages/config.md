# cmx vm config

## Overview

Manage the CLI configuration stored in `~/.config/cloudmesh/clouds.yaml`.

### Sub‑commands

- **`get KEY`** – Get a specific configuration value.
- **`init`** – Initialize the VM CLI configuration.
- **`list`** – List all current VM configuration settings.
- **`set KEY VALUE`** – Set a configuration value.

## Usage

```bash
cmx vm config <subcommand> [options]
```

## Examples

```bash
cmx vm config list
cmx vm config get default_cloud
cmx vm config set default_cloud multipass
```
