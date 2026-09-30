# OpenStack Security and SSH

This guide describes SSH key management, security groups, and VM access for OpenStack-based providers such as Chameleon Cloud and Jetstream.

---

## Prerequisites

The OpenStack provider requires the OpenStack CLI to be installed and configured. The active cloud configuration should also include the SSH private key and default VM user when SSH access is required.

**Example configuration:**

```yaml
key_path: ~/.ssh/id_rsa
user: ubuntu
security_group: default
```

> **Note:** The exact image, username, credentials, and security-group requirements may differ between OpenStack deployments.

---

## SSH Key Management

### List Keys
List SSH keys available in the active provider:

```bash
cmx vm key list
```

### Upload a Public Key
Upload an existing public SSH key:

```bash
cmx vm key upload ~/.ssh/id_rsa.pub
```

If no path is supplied, the command defaults to using `~/.ssh/id_rsa.pub`.

A custom cloud key name can also be specified:

```bash
cmx vm key upload ~/.ssh/id_rsa.pub --name my-cloud-key
```

> **Note:** If `--name` is omitted, the OpenStack provider derives the key name from the public-key filename.

### Delete a Key
Delete a key from the active provider:

```bash
cmx vm key delete my-cloud-key
```

> **Important:** Deleting the cloud copy of a public key does **not** delete your local private key.

---

## Security Groups

Security groups control network access to OpenStack VMs.

### List Security Groups
```bash
cmx vm security-group list
```

### Inspect a Security Group
```bash
cmx vm security-group info default
```

### Create a Security Group
Create a group for SSH access:

```bash
cmx vm security-group create ssh-access \
    --description "Allow SSH access"
```

### Add an SSH Rule
Allow inbound TCP port 22 from a trusted network:

```bash
cmx vm security-group rule add ssh-access \
    --protocol tcp \
    --port 22 \
    --cidr 192.0.2.0/24 \
    --direction ingress
```

> **Security Tip:** Replace `192.0.2.0/24` with the specific network that should be allowed to connect. Avoid using `0.0.0.0/0` for SSH unless public SSH access is intentionally required. Restricting the CIDR reduces unnecessary exposure of port 22.

### List Rules
```bash
cmx vm security-group rule list ssh-access
```

### Associate the Group with a VM
```bash
cmx vm security-group add my-vm ssh-access
```

### Remove the Group from a VM
```bash
cmx vm security-group remove my-vm ssh-access
```

### Remove a Rule
First, obtain the rule ID:

```bash
cmx vm security-group rule list ssh-access
```

Then remove it:

```bash
cmx vm security-group rule remove ssh-access <rule-id>
```

### Delete the Security Group
```bash
cmx vm security-group delete ssh-access
```

> **Note:** Remove the group from all associated VMs before attempting to delete it if required by your OpenStack deployment.

---

## Connecting to a VM

Once the VM has network connectivity, an appropriate security group, and the correct SSH key, inspect its connection information:

```bash
cmx vm login my-vm
```

Start an interactive SSH session:

```bash
cmx vm ssh my-vm
```

Generate SSH configuration information:

```bash
cmx vm ssh-config my-vm
```

Run a command remotely:

```bash
cmx vm run my-vm "hostname"
```

The OpenStack implementation uses the configured `key_path` and `user` values when establishing SSH-based connections.

---

## Recommended Workflow

A typical secure setup follows these steps:

1. Create or select an SSH key pair locally.
2. Upload only the public key to OpenStack.
3. Create a dedicated security group.
4. Allow SSH only from the required source CIDR.
5. Associate the security group with the VM.
6. Verify the VM connection information.
7. Connect using `cmx vm ssh` or execute commands with `cmx vm run`.

**Example execution:**

```bash
# Upload public key
cmx vm key upload ~/.ssh/id_rsa.pub --name research-key

# Create security group
cmx vm security-group create research-ssh \
    --description "SSH access for research VM"

# Add inbound SSH rule for trusted CIDR
cmx vm security-group rule add research-ssh \
    --protocol tcp \
    --port 22 \
    --cidr 192.0.2.0/24 \
    --direction ingress

# Attach security group to instance
cmx vm security-group add research-vm research-ssh

# Inspect login info and connect
cmx vm login research-vm
cmx vm ssh research-vm
```

---

## Provider Support

The commands in this guide describe functionality implemented by the OpenStack provider. Chameleon Cloud and Jetstream use the OpenStack provider path, but authentication, images, network configuration, quotas, and site-specific policies may differ.

Other providers may implement only a subset of these operations. For example, a provider may support listing security groups without supporting creation or rule management. Unsupported operations should be handled through the provider feature interface rather than assumed to be available on every cloud.