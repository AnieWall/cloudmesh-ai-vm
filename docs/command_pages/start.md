# cmx vm start

## Overview

Starts or launches a VM.

### Options

- `--count <int>` – Launch a specific number of VMs with automatic naming.
- `--range <range>` – Launch VMs in the specified index range (e.g., `1-5`).

If no name is provided, a name is generated based on `{username}-{counter}`.

## Usage

```bash
cmx vm start [NAME] [options]
```

## Examples

```bash
cmx vm start my-vm
cmx vm start --count 3
cmx vm start --range 1-5
```
