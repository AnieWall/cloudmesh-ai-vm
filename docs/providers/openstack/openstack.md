# OpenStack Provider

OpenStack is a powerful open-source cloud computing platform that provides a unified interface for managing large-scale pools of compute, storage, and networking resources. This provider allows `cloudmesh-ai-vm` to interact with any OpenStack-compliant cloud, including private clouds and specialized research clouds like Chameleon and Jetstream.

## Configuration

The OpenStack provider typically relies on a standard OpenStack `clouds.yaml` file located at `~/.config/openstack/clouds.yaml`.

To define a cloud in `clouds.yaml`:

```yaml
clouds:
  my-openstack-cloud:
    auth:
      auth_url: https://openstack.example.com:5000/v3
      username: "my-user"
      password: "my-password"
      project_domain_id: "default"
      project_id: "my-project-id"
    region_name: "RegionOne"
    interface: "public"
```

You can then set this as your default in the `cloudmesh` configuration:

```yaml
openstack:
  default_cloud: my-openstack-cloud
  image: ubuntu-22.04
  flavor: m1.small
```

## Key Features

- **Scaling**: Easily manage dozens of VMs across different regions.
- **Advanced Lifecycle**: Support for **shelving** (saving VM state and freeing resources) and **unshelving**.
- **Network Control**: Comprehensive management of **Security Groups** and firewall rules.
- **Hardware Profiles**: Use **Flavors** to specify exact CPU, RAM, and disk requirements.

## Examples

```bash
# Set OpenStack as the active provider
cmx vm provider set openstack

# List available flavors in the cloud
cmx vm flavor

# Start a VM using a specific flavor
cmx vm start my-os-vm --flavor m1.medium

# Shelve a VM to free up resources
cmx vm shelve my-os-vm
```
