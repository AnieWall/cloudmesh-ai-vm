import functools
import click
from rich.console import Console

console = Console()

class VMCommandError(Exception):
    """Base exception for VM command errors."""
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)

def handle_errors(f):
    """Decorator to catch VMCommandError and print it cleanly."""
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except VMCommandError as e:
            console.print(f"[bold red]Error:[/bold red] {e.message}")
            raise click.Abort()
        except Exception as e:
            # Check if it's a configuration or provider error
            e_type = type(e).__name__
            if "ConfigError" in e_type or "VMProviderError" in e_type:
                console.print(f"[bold red]Configuration Error:[/bold red] {str(e)}")
                console.print("[yellow]Please check your clouds.yaml configuration and environment variables (e.g., OS_CLOUD).[/yellow]")
            else:
                console.print(f"[bold red]Unexpected Error:[/bold red] {str(e)}")
            raise click.Abort()
    return wrapper
