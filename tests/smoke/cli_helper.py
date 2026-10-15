import os
import yaml
import sys
import traceback
from rich.console import Console
from rich.text import Text
from cloudmesh.ai.common.stopwatch import StopWatch
from cloudmesh.ai.command import vm
from cloudmesh.ai.command.vm._shared.context import state
from cloudmesh.ai.vm.state_manager import StateManager

def print_header(msg):
    print ()
    Console().print(f"\n[bold blue]=== {msg} ===[/bold blue]\n")

def print_debug_info(msg, result):
    print(f"DEBUG: {msg}")
    converted_output = Text(result.output, style="blue")
    print(converted_output)
    print("DEBUG: Exit code:", result.exit_code)
    if result.exception:
        print("DEBUG: Exception:", result.exception)
        print("DEBUG: Exception traceback:")
        traceback.print_exception(type(result.exception), result.exception, result.exception.__traceback__, file=sys.stdout)

class CliStep:
    def __init__(self, msg, timer_name=None):
        self.msg = msg
        self.timer_name = timer_name
        self.timer_ctx = None
        self.result = None
        self._debug_called = False

    def __enter__(self):
        # 1. Timing
        if self.timer_name:
            StopWatch.start(self.timer_name)

        # 2. Header
        print_header(self.msg)
        return self

    def debug(self, msg, result):
        """Explicitly print debug info and mark this step as having debugged."""
        self.result = result
        self._debug_called = True
        print_debug_info(msg, result)

    def __exit__(self, exc_type, exc_val, exc_tb):
        # 1. Automatic debug on CLI failure (non-zero exit code)
        if self.result and self.result.exit_code != 0 and not self._debug_called:
            print_debug_info(f"Step '{self.msg}' failed automatically", self.result)

        # 2. Automatic traceback on Python exception
        if exc_type:
            # Ignore pytest.skip to avoid noise during deliberate skips
            if "Skip" not in exc_type.__name__:
                Console().print(f"\n[bold red]Exception in step '{self.msg}':[/bold red]")
                traceback.print_exception(exc_type, exc_val, exc_tb, file=sys.stdout)

        # 3. Exit timing context
        if self.timer_name:
            StopWatch.stop(self.timer_name)
            value = StopWatch.get(self.timer_name)
            Console().print(f"[bold green]Step '{self.msg}' completed in {value:.2f} seconds[/bold green]\n")

def cli_step(msg, timer_name=None):
    """Context manager for CLI test steps."""
    return CliStep(msg, timer_name)

def setup_cli_config(tmp_path, provider_name, config_data):


    """
    Sets up a temporary config file and injects it into the CLI's state proxy.
    """
    config_dir = tmp_path / ".config" / "cloudmesh"
    config_dir.mkdir(parents=True)
    config_file = config_dir / "clouds.yaml"
    
    # Merge provider config into the base config
    full_config = {
        "username": "smoke_test_user",
        "clouds": {
            provider_name: config_data
        }
    }
    
    with open(config_file, "w") as f:
        yaml.dump(full_config, f)
    
    # Inject a new StateManager instance into the global state proxy
    new_manager = StateManager(str(config_file))
    state.set_manager(new_manager)
    
    return str(config_file)
