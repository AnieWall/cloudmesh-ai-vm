import pytest
from cloudmesh.ai.vm.openstack.JetstreamManager import Provider

@pytest.fixture
def config():
    """Mock configuration for Jetstream provider."""
    return {
        "clouds": {
            "jetstream": {
                "flavor": "m3.medium",
                "num_instances": 1,
            }
        }
    }

@pytest.fixture
def provider(config):
    """Jetstream provider instance."""
    return Provider(config)

@pytest.mark.parametrize(
    "flavor, hours, days, weeks, instances, expected_value",
    [
        ("m3.tiny", 8, 5, 1, 1, 40),            # 1 * 8 * 5 * 1 * 1
        ("g5.4xl", 24, 7, 4, 2, 688128),       # 512 * 24 * 7 * 4 * 2
        ("m3.medium", 12, 5, 52, 1, 24960),    # 8 * 12 * 5 * 52 * 1
    ],
)
def test_get_cost_calculations(provider, flavor, hours, days, weeks, instances, expected_value):
    """Verify the cost formula for various flavors and usage patterns."""
    result = provider.get_cost(
        flavor=flavor,
        hours_per_day=hours,
        days_per_week=days,
        weeks=weeks,
        num_instances=instances,
    )
    assert result["value"] == expected_value
    assert result["unit"] == "SU"

def test_get_cost_defaults(provider):
    """Verify that defaults are used when no arguments are provided."""
    # Default: m3.medium (8 SU/hr), 8h/day, 5d/week, 52w, 1 instance
    # 8 * 8 * 5 * 52 * 1 = 16640
    result = provider.get_cost()
    assert result["value"] == 16640
    assert result["unit"] == "SU"

def test_get_cost_config_overrides(config):
    """Verify that values in the cloud configuration are used if kwargs are missing."""
    config["clouds"]["jetstream"]["flavor"] = "m3.small"  # 2 SU/hr
    config["clouds"]["jetstream"]["num_instances"] = 2

    provider = Provider(config)
    # Defaults for others: 8h/day, 5d/week, 52w
    # 2 * 8 * 5 * 52 * 2 = 8320
    result = provider.get_cost()
    assert result["value"] == 8320

def test_get_cost_unknown_flavor(provider):
    """Verify that an unsupported flavor returns the expected error response."""
    result = provider.get_cost(flavor="invalid-flavor")
    assert result["value"] == "Unknown"
    assert "Error: Unknown instance flavor: invalid-flavor" in result["details"]

def test_get_cost_details(provider):
    """Verify that the details string correctly reflects the inputs."""
    flavor = "m3.large"
    hours = 10
    days = 6
    weeks = 10
    instances = 3

    result = provider.get_cost(
        flavor=flavor,
        hours_per_day=hours,
        days_per_week=days,
        weeks=weeks,
        num_instances=instances,
    )

    details = result["details"]
    assert flavor in details
    assert str(hours) in details
    assert str(days) in details
    assert str(weeks) in details
    assert str(instances) in details
