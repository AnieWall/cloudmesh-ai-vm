import functools

import click
from rich.console import Console

console = Console()


class VMCommandError(Exception):
    """Base exception for VM command errors."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class VMFeatureNotSupported(VMCommandError):
    """Raised when a provider does not support a requested feature (e.g., a console).

    The CLI can catch this exception to provide a graceful fallback (for example,
    falling back to an SSH session when a graphical console is unavailable).
    """

    def __init__(self, feature: str, provider: str | None = None):
        self.feature = feature
        self.provider = provider
        msg = f"Feature '{feature}' not supported"
        if provider:
            msg += f" by provider '{provider}'"
        super().__init__(msg)


def handle_errors(f):
    """Decorator to catch VMCommandError and print it cleanly."""

    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except (VMCommandError, SystemExit) as e:
            if isinstance(e, VMCommandError):
                console.print(f"[bold red]Error:[/bold red] {e.message}")
                raise click.Abort()
            raise e
        except Exception as e:
            # Check if it's a configuration or provider error
            e_type = type(e).__name__
            if "ConfigError" in e_type or "VMProviderError" in e_type:
                console.print(f"[bold red]Configuration Error:[/bold red] {e!s}")
                console.print(
                    "[yellow]Please check your clouds.yaml configuration and environment variables (e.g., OS_CLOUD).[/yellow]"
                )
            else:
                console.print(f"[bold red]Unexpected Error:[/bold red] {e!s}")
            raise click.Abort()

    return wrapper
