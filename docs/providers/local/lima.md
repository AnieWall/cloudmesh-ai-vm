# Lima Provider

Lima (Linux Machines) is a lightweight VM manager for macOS and Linux, providing a seamless way to run Linux virtual machines. It uses QEMU under the hood and provides an easy way to share files and ports between the host and the guest.

## Configuration

In your `clouds.yaml`, you can configure the default resources and image for Lima VMs:

```yaml
lima:
  image: ubuntu-22.04
  cpus: 2
  memory: 4GiB
  disk: 20GiB
```

## Key Features

- **Host Integration**: Automatic file sharing and port forwarding.
- **QEMU Powered**: Reliable and widely compatible virtualization.
- **Fast Setup**: Quick installation and minimal overhead for local development.

## Examples

```bash
# Set Lima as default
cmx vm provider set lima

# Start a VM with default config
cmx vm start

# List local Lima VMs
cmx vm list
```
