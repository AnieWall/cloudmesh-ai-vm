"""Regression tests: `cmx vm list` must show full VM names in narrow terminals."""

import io
from unittest.mock import patch

from rich.console import Console

from cloudmesh.ai.command._shared import ui
from cloudmesh.ai.command.vm.list import _render_vms
from tests.utils.ip_synthetic import synthetic_ip_pair

LONG_NAME = "test-named-khajashabbirahmed-jetstream-vm"


def _render(width, func, *args, **kwargs):
    """Run func with the shared console redirected to a fixed-width buffer."""
    buffer = io.StringIO()
    with patch.object(ui, "console", Console(file=buffer, width=width)):
        func(*args, **kwargs)
    return buffer.getvalue()


def test_vm_list_shows_full_name_at_80_columns():
    """The smoke tests run at 80 columns and search the output for the VM name."""
    # Use synthetic IPs from the TEST‑NET block (RFC 5737); these addresses are never real hosts.
    fixed_ip, floating_ip = synthetic_ip_pair("testnet")
    vm = {
        "name": LONG_NAME,
        "status": "ACTIVE",
        "ip": floating_ip,
        "image": "Featured-Ubuntu22",
        "flavor": "m3.tiny",
        "ttl": "None",
        "networks": [fixed_ip, floating_ip],
    }

    output = _render(80, _render_vms, "jetstream", [vm])

    assert LONG_NAME in output


def test_render_table_wraps_columns_by_default():
    """Tables that do not ask for no_wrap keep the previous behavior."""
    columns = ["Name", "Description"]
    rows = [[LONG_NAME, "x" * 100]]

    output = _render(40, ui.render_table, "Security Groups", columns, rows)

    assert LONG_NAME not in output
