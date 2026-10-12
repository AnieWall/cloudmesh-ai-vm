import click
from typing import Optional
from ._shared.context import console, get_active_provider, vm_options, state
from ._shared.exceptions import handle_errors, VMCommandError
import json
import yaml

@click.command()
@click.pass_context
@click.argument("name", required=False, default=None)
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    default=False,
    help="Print the VM information as JSON (YAML is the default)",
)
@click.option(
    "--kind",
    default="vm",
    help="Type of information to return (e.g., 'vm', 'all', 'list')",
)
@vm_options
@handle_errors
def info(ctx: click.Context,
         name: Optional[str] = None,
         as_json: bool = False,   # ← new argument
         kind: str = "vm",
         **kwargs) -> None:
    """
    Get detailed information about a specific VM.
    """
    provider = get_active_provider(ctx)
    
    # 1. Fetch VM information
    if name is None:
        from ._shared.context import resolve_vm_name
        name = resolve_vm_name(ctx, name)

    vm_info = provider.info(name, kind=kind)
    
    if not vm_info:
        raise VMCommandError(f"No information found for VM '{name}'.")
    
    if "error" in vm_info:
        raise VMCommandError(f"Could not retrieve info for VM '{name}': {vm_info['error']}")


    # 2. Display the information
    console.print(f"\n[bold blue]Information for VM: {name}[/bold blue]")
    console.print("-" * 30)

    # 2. Choose the output format
    if as_json:
        # JSON – compact but still pretty‑printed
        console.print(json.dumps(vm_info, indent=2, sort_keys=True))
    else:
        # YAML – this is now the *default* format
        # safe_dump keeps the output deterministic and human‑readable
        yaml_str = yaml.safe_dump(vm_info, sort_keys=False, default_flow_style=False)
        # Replace yellow (default for some YAML values) with blue for IDs/UUIDs
        import re
        # Regex to match UUIDs: 8-4-4-4-12 hex chars
        uuid_pattern = r'([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})'
        yaml_str = re.sub(uuid_pattern, r'[blue]\1[/blue]', yaml_str)
        console.print(yaml_str)

    
    # Iterate through the returned dictionary and print key-value pairs
    #for key, value in vm_info.items():
    #    # Format keys to be more human-readable (e.g., "public_ip" -> "Public IP")
    #    display_key = key.replace("_", " ").title()
    #    console.print(f"[bold]{display_key}:[/bold] {value}")
    
    console.print("-" * 30)

cmd = info
