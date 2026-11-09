# cmx vm list

## Overview

List VM resources.

### Options

- `--all` – List resources from all enabled providers.

Typical sub‑commands:

- `vms` – List all VMs in the active cloud.
- `regions` – List available regions for the current provider.

## Usage

```bash
cmx vm list [subcommand] [options]
```

## Examples

```bash
cmx vm list vms
cmx vm list regions
cmx vm list --all vms
```
