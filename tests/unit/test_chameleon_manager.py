import pytest
from unittest.mock import MagicMock, patch
from cloudmesh.ai.vm.openstack.ChameleonManager import Provider
from cloudmesh.ai.vm.exceptions import VMProviderError

@pytest.fixture
def mock_config():
    return {
        "clouds": {
            "chameleon": {
                "site": "kvm@tacc",
                "project_name": "test-project",
                "auth_url": "https://api.tacc.chameleoncloud.org/v3",
                "username": "test-user",
                "password": "test-password",
                "domain_name": "Default"
            }
        }
    }

@pytest.fixture
def provider(mock_config):
    p = Provider(mock_config)
    return p

def test_list_regions(provider):
    # Mock the chi.context.list_sites response
    with patch("cloudmesh.ai.vm.openstack.ChameleonManager.chi") as mock_chi:
        mock_chi.context.list_sites.return_value = {
            "kvm@tacc": {"description": "TACC KVM site", "status": "active"},
            "kvm@clemson": {"description": "Clemson KVM site", "status": "active"}
        }

        regions = provider.list_regions()

        assert isinstance(regions, list)
        assert len(regions) == 2
        # Specifically verify the requested region
        tacc_region = next((r for r in regions if r["name"] == "kvm@tacc"), None)
        assert tacc_region is not None
        assert tacc_region["description"] == "TACC KVM site"

def test_create_reservation_success(provider):
    with patch("cloudmesh.ai.vm.openstack.ChameleonManager.chi") as mock_chi:
        # Mock lease duration
        mock_chi.lease.lease_duration.return_value = ("2026-10-06", "2026-10-07")

        result = provider.create_reservation(
            name="smoke-reservation",
            node_type="bare_metal",
            count=1,
            duration=1
        )

        assert result is True
        mock_chi.use_site.assert_called_once_with("kvm@tacc")
        mock_chi.set.assert_called_with("project_name", "test-project")
        mock_chi.lease.create_lease.assert_called_once()

def test_create_reservation_no_project(provider):
    # Modify config to remove project_name
    provider.config["clouds"]["chameleon"]["project_name"] = None

    result = provider.create_reservation(
        name="smoke-reservation",
        node_type="bare_metal",
        count=1
    )

    assert result is False

def test_get_account_info_success(provider):
    with patch("cloudmesh.ai.vm.openstack.ChameleonManager.chi") as mock_chi:
        mock_chi.get.side_effect = lambda key: {
            "project_id": "proj-123",
            "user_id": "user-456",
            "allocation": "1000 SU"
        }.get(key)

        info = provider.get_account_info()

        assert info["site"] == "kvm@tacc"
        assert info["project_name"] == "test-project"
        assert info["project_id"] == "proj-123"
        assert info["user_id"] == "user-456"
        assert info["allocation"] == "1000 SU"
