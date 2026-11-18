import shutil

import pytest

from cloudmesh.ai.vm.factory import factory
from cloudmesh.ai.vm.state_manager import StateManager


@pytest.fixture
def state_manager(tmp_path):
    """Provides a StateManager with a temporary config file."""
    config_dir = tmp_path / ".config" / "cloudmesh"
    config_dir.mkdir(parents=True)
    config_file = config_dir / "clouds.yaml"

    # We'll allow the actual tests to populate this file if needed,
    # or use the default system config.
    return StateManager(str(config_file))


@pytest.fixture
def get_provider(state_manager):
    """
    Fixture to create a provider.
    Usage: get_provider("aws")
    """

    def _get_provider(cloud_name):
        return factory.create(cloud_name, state_manager.config)

    return _get_provider


def skip_if_no_binary(binary_name):
    """Decorator/Helper to skip tests if a required binary is missing."""
    if shutil.which(binary_name) is None:
        pytest.skip(f"Required binary {binary_name} not found. Skipping test.")


@pytest.fixture
def aws_live_provider():
    """Create an AWS provider only for explicitly enabled live tests."""
    import os
    from pathlib import Path

    if os.environ.get("CLOUDMESH_AWS_LIVE_TEST") != "1":
        pytest.skip(
            "Live AWS lifecycle test disabled; "
            "set CLOUDMESH_AWS_LIVE_TEST=1 to enable it"
        )

    config_path = os.environ.get("CLOUDMESH_VM_CONFIG")
    if not config_path:
        pytest.skip("CLOUDMESH_VM_CONFIG is required for live AWS tests")

    path = Path(config_path).expanduser()
    if not path.is_file():
        pytest.skip("AWS configuration file does not exist")

    state_manager = StateManager(str(path))
    aws_config = state_manager.get_cloud_config("aws")

    required = ("access_key", "secret_key", "image")
    missing = [key for key in required if not aws_config.get(key)]

    if not (aws_config.get("flavor") or aws_config.get("size")):
        missing.append("flavor or size")

    if missing:
        pytest.skip(
            "AWS configuration incomplete; missing: " + ", ".join(missing)
        )

    from cloudmesh.ai.vm.aws.AwsManager import Provider

    return Provider(config=state_manager)
