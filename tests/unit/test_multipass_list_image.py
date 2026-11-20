import json
from unittest.mock import MagicMock

from cloudmesh.ai.vm.local.MultipassManager import Provider


def make_provider(items):
    """Create a Provider instance with a mocked _run_command returning the
    supplied ``items`` as the ``list`` JSON output.
    """
    config = {"clouds": {"multipass": {"image": "24.04"}}}
    provider = Provider(config)
    # Mock the command that fetches the VM list; we only need to mock one call.
    provider._run_command = MagicMock(
        return_value=MagicMock(
            stdout=json.dumps({"list": items}),
            returncode=0,
        )
    )
    return provider


def test_list_includes_image_release():
    provider = make_provider([
        {
            "name": "test-running",
            "state": "Running",
            "ipv4": ["10.97.0.56"],
            "release": "24.04 LTS",
        }
    ])

    vms = provider.list()

    assert len(vms) == 1
    assert vms[0]["name"] == "test-running"
    assert vms[0]["status"] == "Running"
    assert vms[0]["ip"] == "10.97.0.56"
    assert vms[0]["image"] == "24.04 LTS"

    provider._run_command.assert_called_once_with(
        ["multipass", "list", "--format", "json"],
        stream=False,
    )


def test_list_stopped_vm_without_ip():
    provider = make_provider([
        {
            "name": "test-stopped",
            "state": "Stopped",
            "ipv4": [],
            "release": "22.04 LTS",
        }
    ])

    vms = provider.list()

    assert vms[0]["status"] == "Stopped"
    assert vms[0]["ip"] == ""
    assert vms[0]["image"] == "22.04 LTS"


def test_list_missing_release_uses_empty_string():
    provider = make_provider([
        {
            "name": "test-unknown",
            "state": "Running",
            "ipv4": [],
        }
    ])

    assert provider.list()[0]["image"] == ""


def test_list_empty_instances():
    provider = make_provider([])

    assert provider.list() == []
