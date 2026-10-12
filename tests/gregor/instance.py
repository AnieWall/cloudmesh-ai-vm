import json
import yaml
import datetime
import sys
from cloudmesh.ai.vm.providers import get_provider
import chi.server
import chi.lease
import chi.network

def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()
    return str(obj)

def initialize_chameleon_auth():
    """Initializes the chameleon provider and sets up the chi context. Returns provider if successful."""
    try:
        provider = get_provider("chameleon")
        provider._setup_chi_context()
        return provider
    except Exception as e:
        print(f"Error initializing provider: {e}")
        return None

def get_instance_from_name(instance_name):
    """Retrieves an instance object by its name."""
    if not initialize_chameleon_auth():
        return None
    print("========")
    try:
        instances = chi.server.list_servers()
        for instance in instances:

            print (instance)

            if getattr(instance, "name", None) == instance_name:
                return instance
    except Exception as e:
        print(f"Error fetching instance details for {instance_name}: {e}")
    print("========")
        
    return None

def get_reservation_details(reservation_id):
    """Finds the lease and reservation details for a given reservation ID."""
    try:
        leases = chi.lease.list_leases()
        res_types = ["flavor_reservations", "node_reservations", "fip_reservations", "network_reservations", "device_reservations"]

        for l in leases:
            for res_type in res_types:
                reservations = getattr(l, res_type, [])
                for res in reservations:
                    r_id = res.get("id") if isinstance(res, dict) else getattr(res, "id", None)
                    if r_id == reservation_id:
                        def get_val(obj, key, default="N/A"):
                            if isinstance(obj, dict): return obj.get(key, default)
                            return getattr(obj, key, default)

                        return {
                            "lease": {
                                "name": get_val(l, "name"),
                                "id": get_val(l, "id"),
                                "status": get_val(l, "status"),
                                "start_date": get_val(l, "start_date"),
                                "end_date": get_val(l, "end_date"),
                            },
                            "reservation": {
                                "id": get_val(res, "id"),
                                "resource_type": get_val(res, "resource_type"),
                                "status": get_val(res, "status"),
                                "resource_properties": get_val(res, "resource_properties"),
                                "amount": get_val(res, "amount"),
                            }
                        }
    except Exception as e:
        return {"error": f"Could not fetch reservation details: {e}"}
    return None

def get_security_group_details(server):
    """Retrieves security groups and their rules for the server."""
    try:
        # Attempt to find security groups in the server object
        sgs = getattr(server, "security_groups", [])

        if not sgs:
            # Try the connection's compute client as a fallback
            conn = getattr(server, "conn", None)
            if conn:
                try:
                    server_id = getattr(server, "id", None)
                    server_details = conn.compute.get_server(server_id)
                    sgs = getattr(server_details, "security_groups", [])
                except Exception:
                    pass

        if not sgs:
            return []

        sg_details = []
        for sg in sgs:
            name = sg.get("name") if isinstance(sg, dict) else getattr(sg, "name", str(sg))
            try:
                # Use chi.network to get rules for this SG
                result = chi.network.neutron().list_security_group_rules(name)
                rules = result.get("security_group_rules", []) if isinstance(result, dict) else result

                seen_rules = set()
                unique_rules = []
                for r in rules:
                    rule_data = {
                        "protocol": r.get("protocol") if isinstance(r, dict) else getattr(r, "protocol", "Unknown"),
                        "port_range_min": r.get("port_range_min") if isinstance(r, dict) else getattr(r, "port_range_min", "Unknown"),
                        "port_range_max": r.get("port_range_max") if isinstance(r, dict) else getattr(r, "port_range_max", "Unknown"),
                        "remote_ip": r.get("remote_ip_prefix") if isinstance(r, dict) else getattr(r, "remote_ip_prefix", "Unknown"),
                        "direction": r.get("direction") if isinstance(r, dict) else getattr(r, "direction", "Unknown"),
                    }
                    # Clean up None values to "Any"
                    for key, val in rule_data.items():
                        if val is None:
                            rule_data[key] = "Any"

                    # Deduplicate
                    rule_tuple = tuple(rule_data.items())
                    if rule_tuple not in seen_rules:
                        seen_rules.add(rule_tuple)
                        unique_rules.append(rule_data)

                sg_details.append({
                    "name": name,
                    "rules": unique_rules
                })
            except Exception as e:
                sg_details.append({"name": name, "error": f"Could not fetch rules: {e}"})
        return sg_details
    except Exception as e:
        return {"error": f"Could not fetch security groups: {e}"}

def get_uuid(instance_name):
    """Resolves a VM name to its UUID."""
    if not initialize_chameleon_auth():
        return None
    try:
        # Attempt to use the built-in get_server_id if available
        if hasattr(chi.server, "get_server_id"):
            uuid = chi.server.get_server_id(instance_name)
            if uuid:
                return uuid
    except Exception:
        pass

    try:
        # Fallback: list all servers and filter by name
        servers = chi.server.list_servers()
        if servers:
            for s in servers:
                # Use getattr to safely access name and id
                s_name = getattr(s, "name", None)
                s_id = getattr(s, "id", None)
                if s_name == instance_name:
                    return s_id
    except Exception:
        pass

    return None

def get_instance_details(server):
    # 1. Use the provider system for authentication (same as cmx vm list)
    provider = initialize_chameleon_auth()
    if not provider:
        return None

    instance_name = getattr(server, "name", "Unknown")
    actual_id = getattr(server, "id", instance_name)

    # 2. Get high-level info from the provider
    try:
        info = provider.info(actual_id)
    except Exception as e:
        print(f"Warning: Could not get provider info for {actual_id}: {e}")
        info = {}

    # 3. Use the server object we already have for deep-dive info
    try:
        # Extract and clean attributes from the server object
        raw_attrs = server.__dict__.copy()
        cleaned_attrs = {}
        for k, v in raw_attrs.items():
            if hasattr(v, "__dict__") or isinstance(v, (set, complex)):
                cleaned_attrs[k] = str(v)
            elif isinstance(v, list):
                cleaned_attrs[k] = [str(i) if hasattr(i, "__dict__") else i for i in v]
            else:
                cleaned_attrs[k] = v

        raw_details = {
            "raw_attributes": cleaned_attrs,
            "addresses": getattr(server, "addresses", {}),
            "status": getattr(server, "status", "Unknown"),
            "id": getattr(server, "id", "Unknown"),
            "name": getattr(server, "name", "Unknown"),
        }

        # Resolve Reservation Details
        reservation_info = None
        flavor_name = getattr(server, "flavor_name", "")
        if flavor_name and flavor_name.startswith("reservation:"):
            res_id = flavor_name.split(":", 1)[1]
            reservation_info = get_reservation_details(res_id)

        # Enhance Provider Info with Flavor details from resource_properties
        if reservation_info and "reservation" in reservation_info:
            res_props_raw = reservation_info["reservation"].get("resource_properties", "{}")
            try:
                res_props = json.loads(res_props_raw) if isinstance(res_props_raw, str) else res_props_raw

                info["Flavor"] = {
                    "id": res_props.get("id"),
                    "name": res_props.get("name"),
                    "ram": res_props.get("ram"),
                    "disk": res_props.get("disk"),
                    "vcpus": res_props.get("vcpus"),
                    "extra_specs": res_props.get("extra_specs"),
                    "reservation_id": res_id
                }
            except Exception:
                pass

        # Resolve Security Group Details
        sg_info = get_security_group_details(server)

        # Add simplified security group info to vm_info
        if isinstance(sg_info, list):
            simplified_sgs = []
            for sg in sg_info:
                if not isinstance(sg, dict) or "name" not in sg:
                    continue

                name = sg["name"]
                rules_summary = []
                for r in sg.get("rules", []):
                    if not isinstance(r, dict): continue

                    proto = r.get("protocol", "Any")
                    p_min = r.get("port_range_min", "Any")
                    p_max = r.get("port_range_max", "Any")
                    remote = r.get("remote_ip", "Any")
                    direction = r.get("direction", "Unknown")

                    # High-level simplifications
                    if proto == "Any" and p_min == "Any" and remote == "Any":
                        summary = f"All {direction}"
                    elif proto == "icmp" and p_min == "Any" and remote == "Any":
                        summary = f"ICMP {direction}"
                    elif proto == "tcp" and p_min == "22" and p_max == "22":
                        remote_label = "All" if remote in ["0.0.0.0/0", "Any"] else remote
                        summary = f"SSH {direction} from {remote_label}"
                    else:
                        port_str = f"{p_min}-{p_max}" if p_min != p_max else str(p_min)
                        remote_label = "All" if remote in ["0.0.0.0/0", "Any"] else remote
                        summary = f"{proto} {port_str} {direction} from {remote_label}"

                    if summary not in rules_summary:
                        rules_summary.append(summary)

                simplified_sgs.append({
                    "name": name,
                    "summary": "; ".join(rules_summary) if rules_summary else "No rules"
                })
            info["SecurityGroups"] = simplified_sgs
        elif isinstance(sg_info, dict) and "error" in sg_info:
            info["SecurityGroups"] = sg_info["error"]

        full_details = {
            "chi_raw_details": raw_details,
            "reservation_details": reservation_info,
            "security_groups": sg_info,
            "vm_info": info
        }
    except Exception as e:
        print(f"Error extracting details from server object: {e}")
        full_details = info

    return full_details

    return full_details

if __name__ == "__main__":
    if len(sys.argv) > 1:
        instance_name = sys.argv[1]
    else:
        instance_name = "gregor-chameleon-tacc-210"

    print(f"Fetching detailed information for instance: {instance_name}...")

    target_instance = get_instance_from_name(instance_name)
    if target_instance:
        details = get_instance_details(target_instance)
    else:
        details = None

    if details:
        print("\n--- Instance Details (JSON) ---")
        print(json.dumps(details, indent=4, default=json_serial))

        print("\n--- Instance Details (YAML) ---")
        def make_serializable(obj):
            if isinstance(obj, dict):
                return {k: make_serializable(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [make_serializable(i) for i in obj]
            elif isinstance(obj, (datetime.datetime, datetime.date)):
                return obj.isoformat()
            return str(obj) if not isinstance(obj, (int, float, bool, type(None))) else obj

        print(yaml.dump(make_serializable(details), default_flow_style=False, sort_keys=False))
    else:
        print("Could not retrieve details for the instance.")
