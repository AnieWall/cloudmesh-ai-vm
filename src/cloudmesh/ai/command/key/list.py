import click
import json
from cloudmesh.ai.command._shared.context import console, get_active_provider
from cloudmesh.ai.command._shared.exceptions import handle_errors
from cloudmesh.ai.command._shared.ui import render_table

@click.command()
@click.option("--all", is_flag=True, help="List keys from all enabled providers")
@click.option("--json", "as_json", is_flag=True, help="Output results in JSON format")
@click.pass_context
@handle_errors
def list_keys(ctx: click.Context, all: bool, as_json: bool):
    """List all SSH keys for the current provider."""
    if all:
        from cloudmesh.ai.vm.providers import PROVIDER_MAP, get_provider
        from cloudmesh.ai.command._shared.context import state

        config = state.config
        configured_clouds = config.db.get("clouds", {}) if config else {}

        any_keys = False
        all_results = {}
        for cloud_name in sorted(PROVIDER_MAP.keys()):
            cloud_cfg = configured_clouds.get(cloud_name)
            is_enabled = False
            if cloud_cfg:
                if hasattr(cloud_cfg, 'enabled'):
                    is_enabled = cloud_cfg.enabled
                elif isinstance(cloud_cfg, dict):
                    is_enabled = cloud_cfg.get('enabled', False)

            if not is_enabled:
                continue

            try:
                provider = get_provider(cloud_name)
                keys = provider.get_keys()
                if keys:
                    all_results[cloud_name] = keys
                    if not as_json:
                        render_table(f"SSH Keys on {cloud_name}", ["Name", "Fingerprint"], [[k.get("name"), k.get("fingerprint", "N/A")] for k in keys])
                    any_keys = True
            except Exception as e:
                console.print(f"Could not list keys for provider {cloud_name}: {e}")

        if as_json:
            console.print(json.dumps(all_results, indent=2))
        elif not any_keys:
            console.print("No SSH keys found on any enabled providers.")
        return

    provider = get_active_provider(ctx)
    keys = provider.get_keys()
    if keys:
        if as_json:
            console.print(json.dumps(keys, indent=2))
        else:
            render_table("SSH Keys", ["Name", "Fingerprint"], [[k.get("name"), k.get("fingerprint", "N/A")] for k in keys])
    else:
        console.print("No SSH keys found.")

cmd = list_keys
