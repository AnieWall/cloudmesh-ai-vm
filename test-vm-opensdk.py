Below is a **complete, ready‑to‑run Python script** that

1. reads your OpenStack credentials from `~/.config/openstack/clouds.yaml` (the same way the OpenStack CLI does),  
2. creates (or re‑uses) a keypair that points at the public key in `~/.ssh/id_rsa.pub`,  
3. boots a VM on **Jetstream‑2** (you just need to tell the script which **cloud name**, **image**, **flavor**, **network**, and **security group** you want to use),  
4. allocates a **floating (public) IP**, and  
5. attaches that floating IP to the newly‑created server so you can SSH to it with your local key.

---

### 1️⃣  Prerequisites

| What you need | How to get it |
|---------------|---------------|
| **Python 3.8+** | `python3 --version` |
| **OpenStack SDK** | `pip install openstacksdk` (or add it to `requirements.txt` below) |
| **Your OpenStack clouds.yaml** | already at `~/.config/openstack/clouds.yaml` |
| **A public SSH key** | `~/.ssh/id_rsa.pub` (or any other key you prefer) |
| **Jetstream‑2 project/tenant** | the cloud entry in `clouds.yaml` must point to your Jetstream‑2 project |

> **Tip:** If you have multiple keys, point `SSH_KEY_PATH` to the one you want the VM to trust.

---

### 2️⃣  `requirements.txt`

```text
openstacksdk>=0.102
```

Install with:

```bash
pip install -r requirements.txt
```

---

### 3️⃣  The Python program (`create_jetstream_vm.py`)

```python
#!/usr/bin/env python3
"""
Create a VM on Jetstream‑2 with a public (floating) IP that you can SSH to
using the SSH key stored at ~/.ssh/id_rsa.pub.

The script expects a clouds.yaml entry for Jetstream‑2 (e.g. cloud name
'jetstream2').  All other parameters (image, flavor, network, security group)
are supplied via command‑line arguments or can be hard‑coded below.

Author:  ChatGPT
"""

import argparse
import os
import sys
import time
from pathlib import Path

import openstack

# ----------------------------------------------------------------------
# Configuration – change these defaults to match your environment
# ----------------------------------------------------------------------
DEFAULT_CLOUD = "jetstream2"               # name of the entry in clouds.yaml
DEFAULT_NETWORK = "public"                 # name (or ID) of the private network to launch on
DEFAULT_SECURITY_GROUP = "default"         # name (or ID) of a security group that allows SSH (port 22)
DEFAULT_KEYPAIR_NAME = "my_jetstream_key"  # will be created if it does not exist
SSH_KEY_PATH = Path.home() / ".ssh/id_rsa.pub"
# ----------------------------------------------------------------------


def get_connection(cloud_name: str) -> openstack.connection.Connection:
    """Load clouds.yaml and return an authenticated Connection."""
    try:
        conn = openstack.connect(cloud=cloud_name)
        # Touch the identity service to make sure we really are authenticated
        conn.authorize()
        return conn
    except Exception as exc:
        sys.exit(f"❌ Failed to connect to cloud '{cloud_name}': {exc}")


def ensure_keypair(conn: openstack.connection.Connection,
                   keypair_name: str,
                   pubkey_path: Path) -> str:
    """
    Ensure a keypair with *keypair_name* exists.
    If it does not, create it from the public key file at *pubkey_path*.
    Returns the name of the keypair (it may be different if the cloud
    forced a rename, e.g. appending a UUID).
    """
    if not pubkey_path.is_file():
        sys.exit(f"❌ Public key not found at {pubkey_path}")

    # Load public key content
    with pubkey_path.open("r") as f:
        public_key = f.read().strip()

    # Check if a keypair with that name already exists
    existing = conn.compute.find_keypair(keypair_name)
    if existing:
        # Verify the stored public key matches – if not, warn the user.
        if existing.public_key.strip() != public_key:
            print(
                f"⚠️  Keypair '{keypair_name}' exists but its public key differs from"
                f" {pubkey_path}.  Using the existing keypair."
            )
        else:
            print(f"🔑 Using existing keypair '{keypair_name}'.")
        return existing.name

    # Create a new keypair
    print(f"🔑 Creating keypair '{keypair_name}' from {pubkey_path} …")
    kp = conn.compute.create_keypair(name=keypair_name, public_key=public_key)
    print(f"✅ Keypair created: {kp.name}")
    return kp.name


def find_resource(conn: openstack.connection.Connection, res_type: str, name_or_id: str):
    """
    Helper that looks up a resource (image, flavor, network, security group)
    by name or UUID.  Raises SystemExit if not found.
    """
    finder = {
        "image": conn.compute.find_image,
        "flavor": conn.compute.find_flavor,
        "network": conn.network.find_network,
        "sg": conn.network.find_security_group,
    }.get(res_type)

    if not finder:
        raise ValueError(f"Unsupported resource type: {res_type}")

    obj = finder(name_or_id, ignore_missing=True)
    if not obj:
        sys.exit(f"❌ Could not find {res_type} '{name_or_id}'.  List available ones with:\n"
                 f"   openstack {res_type} list")
    return obj


def allocate_floating_ip(conn: openstack.connection.Connection,
                         external_network_name: str = "public") -> openstack.network.v2.floating_ip.FloatingIP:
    """
    Allocate a floating IP from the external network (by default 'public').
    """
    ext_net = find_resource(conn, "network", external_network_name)
    fip = conn.network.create_ip(floating_network_id=ext_net.id)
    print(f"🌐 Allocated floating IP: {fip.floating_ip_address}")
    return fip


def create_server(conn: openstack.connection.Connection,
                  name: str,
                  image,
                  flavor,
                  network,
                  security_group,
                  key_name: str) -> openstack.compute.v2.server.Server:
    """
    Boot a server and wait until it becomes ACTIVE.
    """
    print(f"🚀 Booting server '{name}' …")
    server = conn.compute.create_server(
        name=name,
        image_id=image.id,
        flavor_id=flavor.id,
        networks=[{"uuid": network.id}],          # attach to the private network
        security_groups=[{"name": security_group.name}],
        key_name=key_name,
    )
    # Wait for the status to become ACTIVE (or ERROR)
    server = conn.compute.wait_for_server(server, status="ACTIVE", failures=["ERROR"], interval=5, wait=600)
    print(f"✅ Server '{name}' is ACTIVE (ID: {server.id})")
    return server


def attach_floating_ip(conn: openstack.connection.Connection,
                       server,
                       floating_ip) -> None:
    """
    Attach the floating IP to the server's first (or only) port.
    """
    # Retrieve the server's ports
    ports = list(conn.network.ports(device_id=server.id))
    if not ports:
        sys.exit("❌ No ports found on the server – cannot attach floating IP")

    port = ports[0]   # usually there is exactly one port
    print(f"🔗 Attaching floating IP {floating_ip.floating_ip_address} to port {port.id} …")
    conn.network.add_ip_to_port(port, floating_ip)
    print("✅ Floating IP attached.")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Create a Jetstream‑2 VM with a public IP that you can SSH into."
    )
    parser.add_argument("--cloud", default=DEFAULT_CLOUD,
                        help=f"Cloud name from clouds.yaml (default: {DEFAULT_CLOUD})")
    parser.add_argument("--name", required=True,
                        help="Name for the new VM")
    parser.add_argument("--image", required=True,
                        help="Image name or ID")
    parser.add_argument("--flavor", required=True,
                        help="Flavor name or ID")
    parser.add_argument("--network", default=DEFAULT_NETWORK,
                        help=f"Private network to attach (default: {DEFAULT_NETWORK})")
    parser.add_argument("--secgroup", default=DEFAULT_SECURITY_GROUP,
                        help=f"Security group that permits SSH (default: {DEFAULT_SECURITY_GROUP})")
    parser.add_argument("--keypair", default=DEFAULT_KEYPAIR_NAME,
                        help=f"Keypair name to create/use (default: {DEFAULT_KEYPAIR_NAME})")
    parser.add_argument("--keyfile", default=str(SSH_KEY_PATH),
                        help=f"Public key file to upload (default: {SSH_KEY_PATH})")
    parser.add_argument("--ext-net", default="public",
                        help="External network for floating IP allocation (default: public)")
    parser.add_argument("--wait", type=int, default=600,
                        help="Maximum seconds to wait for the server to become ACTIVE")
    return parser.parse_args()


def main():
    args = parse_args()

    # ------------------------------------------------------------------
    # 1️⃣  Connect to OpenStack
    # ------------------------------------------------------------------
    conn = get_connection(args.cloud)

    # ------------------------------------------------------------------
    # 2️⃣  Resolve resources (image, flavor, network, security group)
    # ------------------------------------------------------------------
    image = find_resource(conn, "image", args.image)
    flavor = find_resource(conn, "flavor", args.flavor)
    network = find_resource(conn, "network", args.network)
    secgroup = find_resource(conn, "sg", args.secgroup)

    # ------------------------------------------------------------------
    # 3️⃣  Ensure our SSH public key is registered as a keypair
    # ------------------------------------------------------------------
    keypair_name = ensure_keypair(conn, args.keypair, Path(args.keyfile))

    # ------------------------------------------------------------------
    # 4️⃣  Allocate a floating IP (public address)
    # ------------------------------------------------------------------
    fip = allocate_floating_ip(conn, external_network_name=args.ext_net)

    # ------------------------------------------------------------------
    # 5️⃣  Boot the server
    # ------------------------------------------------------------------
    server = create_server(
        conn,
        name=args.name,
        image=image,
        flavor=flavor,
        network=network,
        security_group=secgroup,
        key_name=keypair_name,
    )

    # ------------------------------------------------------------------
    # 6️⃣  Attach the floating IP to the server
    # ------------------------------------------------------------------
    attach_floating_ip(conn, server, fip)

    # ------------------------------------------------------------------
    # 7️⃣  Show the final SSH command for the user
    # ------------------------------------------------------------------
    print("\n🔎  All done!  Connect to your VM with:")
    print(f"   ssh -i ~/.ssh/id_rsa {server.name}@{fip.floating_ip_address}")
    print("\nTip: if you used a custom private key, replace the path after -i.")
    print("\n🧹  (Optional) Remember to clean up when you are finished:")
    print(f"   openstack server delete {server.id}")
    print(f"   openstack floating ip delete {fip.id}")

if __name__ == "__main__":
    main()
```

---

### 4️⃣  How to run the script

```bash
# 1️⃣  Make it executable (optional)
chmod +x create_jetstream_vm.py

# 2️⃣  Example run – replace the placeholders with actual values from your Jetstream2 cloud
./create_jetstream_vm.py \
    --name my-test-vm \
    --image "Ubuntu 22.04" \
    --flavor "m1.large" \
    --network "private" \
    --secgroup "default"
```

**Explanation of the arguments**

| Argument | What to put |
|----------|------------|
| `--cloud` | The name of the entry in `clouds.yaml` that points at Jetstream‑2 (e.g. `jetstream2`). |
| `--name` | Desired hostname for the new VM. |
| `--image` | Image **name** or **ID** (run `openstack image list` to see options). |
| `--flavor` | Flavor **name** or **ID** (run `openstack flavor list`). |
| `--network` | Private network to attach (run `openstack network list`).  Often it’s called `private` on Jetstream‑2. |
| `--secgroup` | Security group that allows inbound TCP 22 (SSH).  The default `default` group on Jetstream‑2 already has this rule. |
| `--keypair` | Desired name for the keypair; the script will create it if missing. |
| `--keyfile` | Path to **your** public key (`~/.ssh/id_rsa.pub` is the default). |
| `--ext-net` | External/network that provides floating IPs – normally `public`. |

---

### 5️⃣  What the script does, step‑by‑step

1. **Connect** – reads `clouds.yaml` and authenticates.
2. **Find resources** – resolves the image, flavor, private network, and security‑group you asked for.
3. **Keypair handling** – if a keypair with the given name does not exist, it uploads the public key from `~/.ssh/id_rsa.pub`.  
   *If the keypair already exists, the script re‑uses it (it does **not** overwrite the stored key).*
4. **Floating IP allocation** – pulls a free public IP from the external (“public”) network.
5. **Server creation** – boots the VM, attaches the private network and security group, and injects the keypair name so OpenStack injects your public key into `~/.ssh/authorized_keys`.
6. **Floating IP association** – binds the public IP to the VM’s port, making the VM reachable from the internet.
7. **Prints** a handy `ssh` command for you.

---

### 6️⃣  Cleaning up (optional but recommended)

When you no longer need the VM, run:

```bash
openstack server delete <SERVER_ID>
openstack floating ip delete <FLOATING_IP_ID>
```

You can also delete the keypair if you created a temporary one:

```bash
openstack keypair delete my_jetstream_key
```

---

### 7️⃣  Quick checklist (for future reference)

| ✅ | Item |
|----|------|
| ✓ Install `openstacksdk` (`pip install -r requirements.txt`) |
| ✓ Verify `clouds.yaml` has a valid entry for Jetstream‑2 |
| ✓ Have a public SSH key (`~/.ssh/id_rsa.pub`) |
| ✓ Choose image, flavor, network, security‑group that exist on Jetstream‑2 |
| ✓ Run the script, then SSH using the displayed command |
| ✓ Delete resources when done to avoid charges |

---

#### 🎉 That's it!  
Run the script, SSH into the new machine, and you’re ready to start work on Jetstream‑2. If you run into any issues (e.g., “image not found” or “no floating IPs available”), feel free to paste the exact error message and I’ll help you troubleshoot. Happy computing!