"""Verify hyperscaler providers use genuine Apache Libcloud drivers."""

import pytest

from libcloud.compute.providers import get_driver
from libcloud.compute.types import Provider as LibcloudProvider

from cloudmesh.ai.vm.azure.AzureManager import AzureDriver
from cloudmesh.ai.vm.google.GoogleManager import GCEDriver


def test_azure_uses_real_libcloud_driver():
    expected = get_driver(LibcloudProvider.AZURE_ARM)
    assert AzureDriver is expected, (
        "Azure provider must use the actual Libcloud Azure ARM driver"
    )


def test_google_uses_real_libcloud_driver():
    expected = get_driver(LibcloudProvider.GCE)
    assert GCEDriver is expected, (
        "Google provider must use the actual Libcloud GCE driver"
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("service_account_email", None),
        ("service_account_email", ""),
        ("private_key", None),
        ("private_key", "  "),
        ("project_id", None),
        ("project_id", ""),
        ("project_id", 123),
    ],
)
def test_google_rejects_invalid_configuration(field, value):
    """Invalid GCE settings must fail before driver initialization."""
    from unittest.mock import patch

    from cloudmesh.ai.vm.exceptions import VMProviderError
    from cloudmesh.ai.vm.google.GoogleManager import Provider

    config = {
        "clouds": {
            "google": {
                "service_account_email": "test@example.iam.gserviceaccount.com",
                "private_key": "/path/to/key.json",
                "project_id": "test-project",
            }
        }
    }
    if value is None:
        config["clouds"]["google"].pop(field)
    else:
        config["clouds"]["google"][field] = value

    with patch(
        "cloudmesh.ai.vm.google.GoogleManager.GCEDriver"
    ) as mock_driver:
        with pytest.raises(VMProviderError, match=field):
            Provider(config)

        mock_driver.assert_not_called()
