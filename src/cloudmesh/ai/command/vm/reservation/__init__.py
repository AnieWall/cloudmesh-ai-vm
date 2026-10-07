import click
from .duration import duration

@click.group()
def reservation():
    """Manage VM reservations (leases) on the cloud provider."""
    pass

reservation.add_command(duration)

cmd = reservation
