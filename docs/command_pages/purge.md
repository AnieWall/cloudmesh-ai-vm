# cmx vm purge

## Overview

Deletes all VMs, releases all floating IPs, and removes all reservations for the target cloud (or for every enabled cloud when the option is omitted). A safety confirmation prompt is required unless the user supplies `--yes` / `-y` to skip the prompt for scripted usage.

## Usage

```bash
cmx vm purge [--cloud=CLOUD] [--yes | -y]
```

## Examples

```bash
cmx vm purge                # Interactive, all clouds
cmx vm purge --cloud chameleon   # Interactive, only Chameleon
cmx vm purge -y             # Non‑interactive, all clouds
cmx vm purge --cloud multipass -y
```
