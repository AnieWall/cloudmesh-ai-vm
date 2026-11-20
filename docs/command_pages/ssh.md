# cmx vm ssh

## Overview

Starts an interactive SSH session with the VM.

## Usage

```bash
cmx vm ssh [NAME]
```

## Example

```bash
cmx vm ssh my-vm
```

## Note
The `cmx vm ssh` command now automatically resolves the appropriate private SSH key using the shared `resolve_key_path` helper. This ensures the correct private key is used (by stripping the `.pub` suffix if necessary) and eliminates the previous public‑key‑only bug that caused permission errors. Users no longer need to manually specify a key path.
