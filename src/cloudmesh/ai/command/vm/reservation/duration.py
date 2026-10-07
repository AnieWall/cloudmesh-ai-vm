import click
import re
from datetime import datetime, timedelta
from typing import Optional
from .._shared.context import console, get_active_provider, state
from .._shared.exceptions import handle_errors, VMCommandError

def parse_relative_offset(offset_str: str) -> timedelta:
    """
    Parses a relative time offset string like '+10m', '+2h', '+1d'
    and returns a timedelta object.
    """
    match = re.match(r"^\+(\d+)([mhd])$", offset_str)
    if not match:
        raise click.BadParameter(
            f"Invalid offset format '{offset_str}'. Expected '+<number>[m|h|d]' (e.g., '+10m', '+2h', '+1d')."
        )

    value = int(match.group(1))
    unit = match.group(2)

    if unit == 'm':
        return timedelta(minutes=value)
    elif unit == 'h':
        return timedelta(hours=value)
    elif unit == 'd':
        return timedelta(days=value)

    raise click.BadParameter(f"Unsupported time unit '{unit}'. Use 'm' for minutes, 'h' for hours, or 'd' for days.")

@click.command()
@click.argument("name")
@click.option("--node-type", required=True, help="Type of node to reserve (e.g., 'compute_haswell')")
@click.option("--count", type=int, default=1, help="Number of nodes to reserve")
@click.option("--start", help="Relative start time offset (e.g., '+10m', '+1h', '+1d'). Defaults to now.")
@click.option("--days", type=int, default=1, help="Duration of the reservation in days")
@handle_errors
def duration(name: str, node_type: str, count: int, start: Optional[str], days: int) -> None:
    """
    Creates a reservation with a specified duration and relative start time.

    Example:
        cmx vm reservation duration "my-lease" --node-type "compute_haswell" --count 1 --start +10m
    """
    provider = get_active_provider()

    # Verify provider supports reservations
    if not hasattr(provider, 'create_reservation'):
        raise VMCommandError(f"The active provider '{provider.cloud_name}' does not support reservations.")

    # Calculate start and end dates
    now = datetime.now()
    if start:
        delta = parse_relative_offset(start)
        start_dt = now + delta
    else:
        start_dt = now

    end_dt = start_dt + timedelta(days=days)

    # Format dates as "YYYY-MM-DD HH:MM" (required by chi/OpenStack)
    start_date_str = start_dt.strftime("%Y-%m-%d %H:%M")
    end_date_str = end_dt.strftime("%Y-%m-%d %H:%M")

    console.print(f"Creating reservation [bold blue]{name}[/bold blue]...")
    console.print(f"Nodes: {count} x {node_type}")
    console.print(f"Start: {start_date_str}")
    console.print(f"End: {end_date_str}")

    if provider.create_reservation(
        name=name,
        node_type=node_type,
        count=count,
        start_date=start_date_str,
        end_date=end_date_str
    ):
        console.print(f"Successfully created reservation [bold green]{name}[/bold green].")
    else:
        raise VMCommandError(f"Failed to create reservation '{name}'.")

cmd = duration
