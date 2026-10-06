import pytest
import shutil
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

