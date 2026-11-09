# cmx vm status

## Overview

Shows a summary of the current state of the selected cloud (or all enabled clouds when `--cloud` is omitted). The output contains three sections:

1. **Running VMs** – name, status, IP, image, flavor, etc.
2. **Floating IPs** – address, attached VM, status.
3. **Reservations / Leases** – id, type, status, start, end.

Use `--json` to emit the same information as a JSON document.

## Usage

```bash
cmx vm status [--cloud=CLOUD] [--json]
```

## Examples

```bash
cmx vm status                     # All clouds, human‑readable table
cmx vm status --cloud openstack   # Only OpenStack cloud
cmx vm status --json              # JSON output for all clouds
```
