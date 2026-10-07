import argparse
import sys
from pathlib import Path
import yaml
from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver
from libcloud.common.openstack import OpenStackException

def load_cloud_config(cloud_name: str) -> dict:
    clouds_path = Path.home() / ".config" / "openstack" / "clouds.yaml"
    if not clouds_path.is_file():
        sys.exit(f"❌ clouds.yaml not found at {clouds_path}")
    with clouds_path.open() as f:
        data = yaml.safe_load(f) or {}
    clouds = data.get("clouds", data) if isinstance(data, dict) else {}
    if not isinstance(clouds, dict) or cloud_name not in clouds:
        sys.exit(f"❌ Cloud '{cloud_name}' not defined in {clouds_path}")
    cfg = clouds[cloud_name]
    auth = cfg.get("auth", {})
    if not isinstance(auth, dict): auth = {}
    auth_url = auth.get("auth_url") or cfg.get("auth_url")
    if not auth_url:
        sys.exit(f"❌ Could not find 'auth_url' for cloud '{cloud_name}'.")
    user_domain_name = auth.get("user_domain_name") or cfg.get("user_domain_name", "Default")
    project_domain_name = auth.get("project_domain_name") or cfg.get("project_domain_name", "Default")
    region_name = cfg.get("region_name")
    app_cred_id = auth.get("application_credential_id") or cfg.get("application_credential_id")
    app_cred_secret = auth.get("application_credential_secret") or cfg.get("application_credential_secret")
    username = auth.get("username") or cfg.get("username", "")
    password = auth.get("password") or cfg.get("password", "")
    cloud_cfg = {
        "key": username, "password": password, "auth_url": auth_url,
        "ex_force_auth_url_v3": auth_url.rstrip("/").endswith("/v3"),
        "ex_user_domain_name": user_domain_name, "ex_project_domain_name": project_domain_name,
        "region_name": region_name,
    }
    if app_cred_id and app_cred_secret:
        cloud_cfg["ex_application_credential_id"] = app_cred_id
        cloud_cfg["ex_application_credential_secret"] = app_cred_secret
    return cloud_cfg

def get_driver_instance(cloud_cfg: dict):
    OpenStack = get_driver(Provider.OPENSTACK)
    try:
        # we try to pass it explicitly as auth_url
        driver = OpenStack(**cloud_cfg)
        driver.ex_list_keypairs()
        print("✅ Authentication successful!")
        return driver
    except Exception as e:
        print(f"DEBUG: Attempted config: {cloud_cfg}")
        sys.exit(f"❌ Failed to authenticate: {e}")

def main():
    cloud_name = "jetstream"
    print(f"Testing connection to cloud: {cloud_name}...")
    cfg = load_cloud_config(cloud_name)
    driver = get_driver_instance(cfg)
    print("\n🚀 Authentication test passed!")

if __name__ == "__main__":
    main()
