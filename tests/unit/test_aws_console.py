from unittest.mock import MagicMock, patch

import pytest

from cloudmesh.ai.vm.aws.AwsManager import Provider as AwsProvider
from cloudmesh.ai.vm.exceptions import (
    ProviderFeatureNotSupported,
    VMProviderError,
)


@pytest.fixture
def aws_provider():
    provider = AwsProvider.__new__(AwsProvider)
    provider.cloud_name = "aws"
    provider.driver = MagicMock()
    return provider


def test_get_console_returns_libcloud_output(aws_provider):
    node = MagicMock()
    node.id = "i-123456"

    aws_provider.driver.ex_get_console_output.return_value = {
        "instance_id": node.id,
        "timestamp": None,
        "output": "AWS boot console output",
    }

    with patch.object(aws_provider, "_find_node", return_value=node):
        result = aws_provider.get_console("test-vm")

    assert result == "AWS boot console output"
    aws_provider.driver.ex_get_console_output.assert_called_once_with(node)


def test_get_console_missing_instance(aws_provider):
    with patch.object(aws_provider, "_find_node", return_value=None):
        with pytest.raises(VMProviderError, match="not found"):
            aws_provider.get_console("missing-vm")

    aws_provider.driver.ex_get_console_output.assert_not_called()


def test_get_console_libcloud_api_failure(aws_provider):
    node = MagicMock()
    aws_provider.driver.ex_get_console_output.side_effect = RuntimeError(
        "Simulated Libcloud API failure"
    )

    with patch.object(aws_provider, "_find_node", return_value=node):
        with pytest.raises(VMProviderError, match="Failed to retrieve"):
            aws_provider.get_console("test-vm")


@pytest.mark.parametrize("output", [None, ""])
def test_get_console_handles_empty_output(aws_provider, output):
    node = MagicMock()
    aws_provider.driver.ex_get_console_output.return_value = {
        "instance_id": node.id,
        "timestamp": None,
        "output": output,
    }

    with patch.object(aws_provider, "_find_node", return_value=node):
        result = aws_provider.get_console("test-vm")

    assert result == output


def test_get_console_unsupported_type(aws_provider):
    with pytest.raises(ProviderFeatureNotSupported):
        aws_provider.get_console("test-vm", console_type="novnc")

    aws_provider.driver.ex_get_console_output.assert_not_called()
