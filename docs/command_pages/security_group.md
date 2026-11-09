# cmx vm security-group

## Overview

Manage firewall security groups.

### Sub‑commands

- `list` – List all available security groups.
- `info <name>` – Get detailed information and rules.
- `create <name> [--preset PRESET]` – Create a new group (presets: `web-server`, `db-server`, `internal`).
- `delete <name>` – Remove a security group.
- `add <vm> <sg>` – Assign a group to a VM.
- `remove <vm> <sg>` – Unassign a group from a VM.
- `rule [list|add|remove]` – Manage rules within a group.

## Usage

```bash
cmx vm security-group <subcommand> [options]
```
