import time
import webbrowser

import click

from cloudmesh.ai.command._shared.context import (
    console as rich_console,
    get_active_provider,
    resolve_vm_name,
    vm_options,
)
from cloudmesh.ai.command._shared.exceptions import (
    VMCommandError,
    VMFeatureNotSupported,
)
from cloudmesh.ai.vm.exceptions import ProviderFeatureNotSupported


@click.command(name="console")
@click.argument("name", required=False)
@click.option(
    "--type",
    "console_type",
    type=click.Choice(["text", "novnc", "spice"], case_sensitive=False),
    default="text",
    help="Console type – default is plain text streamed to the terminal.",
)
@click.option(
    "-f",
    "--follow",
    is_flag=True,
    default=False,
    help="When using text console, keep polling for new output (like tail -f).",
)
@vm_options
@click.pass_context
def console_cmd(ctx: click.Context, name: str | None = None, console_type: str = "text", follow: bool = False, **kwargs):
    """Open an interactive console to a VM.

    By default (``--type text``) the command prints the VM's serial/text console
    directly in the terminal.  Use ``--type novnc`` or ``--type spice`` to obtain a
    URL for a graphical console and have it opened in the default web browser.
    """
    provider = get_active_provider(ctx)
    vm_name = resolve_vm_name(ctx, name)

    if not vm_name:
        raise VMCommandError("No VM specified and no last‑used VM found in context.")

    try:
        console_output = provider.get_console(vm_name, console_type=console_type)
    except ProviderFeatureNotSupported as e:
        # Provider explicitly indicates the feature is not available – fall back
        # to an SSH session (the existing interactive console experience).
        rich_console.print(
            f"[yellow]Console type '{console_type}' not supported for provider '{provider.cloud_name}'. Falling back to SSH.[/yellow]"
        )
        # Re‑use the existing SSH command implementation.
        from cloudmesh.ai.command.vm.ssh import ssh as ssh_cmd
        ctx.invoke(ssh_cmd, name=vm_name)
        return
    except Exception as e:
        # Convert any unexpected error to a CLI‑friendly message.
        raise VMCommandError(str(e))

    if console_type in ("novnc", "spice"):
        # Assume the returned string is a URL.
        if not console_output:
            raise VMCommandError(f"Console URL not returned for VM {vm_name}.")
        rich_console.print(f"[green]Opening {console_type.upper()} console for {vm_name}...[/green]")
        webbrowser.open(console_output)
        return

    # ``text`` console – print output now, and optionally follow.
    if console_output is None:
        raise VMCommandError(f"No console output available for VM {vm_name}.")

    if not follow:
        rich_console.print(console_output)
        return

    # Follow mode – keep polling and print only new lines.
    printed = ""
    rich_console.print(f"[green]Following console output for {vm_name} (Ctrl‑C to stop)...[/green]")
    try:
        while True:
            new_output = provider.get_console(vm_name, console_type="text")
            if new_output is None:
                break
            # Determine new portion
            if new_output.startswith(printed):
                diff = new_output[len(printed) :]
            else:
                # Console reset or truncated – show everything
                diff = new_output
            if diff:
                rich_console.print(diff, end="")
            printed = new_output
            time.sleep(2)
    except KeyboardInterrupt:
        rich_console.print("\n[yellow]Stopped following console output.[/yellow]")
# Export the command for the dynamic loading (consistent with other commands)
cmd = console_cmd
