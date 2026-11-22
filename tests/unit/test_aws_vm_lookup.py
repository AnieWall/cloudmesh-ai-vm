"""Regression tests for deterministic AWS VM lookup (issue #172)."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from cloudmesh.ai.vm.aws.AwsManager import Provider as AwsProvider


@pytest.fixture
def aws_provider():
    provider = AwsProvider.__new__(AwsProvider)
    provider.cloud_name = "aws"
    provider.driver = MagicMock()
    return provider


def make_node(name, node_id):
    return SimpleNamespace(
        name=name,
        id=node_id,
        state="running",
        public_ips=[],
    )


@pytest.mark.parametrize("reverse_order", [False, True])
def test_find_node_prefers_exact_name_over_id(aws_provider, reverse_order):
    """Exact VM name must win regardless of node-list ordering."""
    identifier = "i-123456"

    node_by_name = make_node(identifier, "i-name-match")
    node_by_id = make_node("production", identifier)

    nodes = [node_by_name, node_by_id]
    if reverse_order:
        nodes.reverse()

    aws_provider.driver.get_node.return_value = node_by_id
    aws_provider.driver.list_nodes.return_value = nodes

    assert aws_provider._find_node(identifier) is node_by_name


@pytest.mark.parametrize(
    ("operation", "driver_method"),
    [
        ("stop", "stop_node"),
        ("delete", "destroy_node"),
    ],
)
def test_lifecycle_targets_exact_name_match(
    aws_provider, operation, driver_method
):
    """AWS lifecycle operations must target the name-matching instance."""
    identifier = "i-123456"

    node_by_name = make_node(identifier, "i-name-match")
    node_by_id = make_node("production", identifier)

    aws_provider.driver.get_node.return_value = node_by_id
    aws_provider.driver.list_nodes.return_value = [
        node_by_id,
        node_by_name,
    ]
    getattr(aws_provider.driver, driver_method).return_value = True

    result = getattr(aws_provider, operation)(identifier)

    assert result is True
    getattr(aws_provider.driver, driver_method).assert_called_once_with(
        node_by_name
    )


@pytest.mark.parametrize("reverse_order", [False, True])
def test_assign_floating_ip_targets_exact_name_match(
    aws_provider, reverse_order
):
    """Elastic IP reuse must resolve the exact VM name."""
    identifier = "i-123456"

    node_by_name = make_node(identifier, "i-name-match")
    node_by_id = make_node("production", identifier)

    nodes = [node_by_name, node_by_id]
    if reverse_order:
        nodes.reverse()

    address = SimpleNamespace(
        ip="203.0.113.10",
        instance_id=node_by_name.id,
        domain="vpc",
        extra={"allocation_id": "eipalloc-123"},
    )

    aws_provider.driver.get_node.return_value = node_by_id
    aws_provider.driver.list_nodes.return_value = nodes
    aws_provider.driver.ex_describe_all_addresses.return_value = [address]
    aws_provider._is_managed_elastic_ip = MagicMock(return_value=True)

    assert aws_provider.assign_floating_ip(identifier) == address.ip

    aws_provider.driver.ex_allocate_address.assert_not_called()
    aws_provider.driver.ex_associate_address_with_node.assert_not_called()


@pytest.mark.parametrize("reverse_order", [False, True])
def test_release_floating_ip_targets_exact_name_match(
    aws_provider, reverse_order
):
    """Elastic IP release must target the name-matching instance."""
    identifier = "i-123456"

    node_by_name = make_node(identifier, "i-name-match")
    node_by_id = make_node("production", identifier)

    nodes = [node_by_name, node_by_id]
    if reverse_order:
        nodes.reverse()

    address = SimpleNamespace(
        ip="203.0.113.10",
        instance_id=node_by_name.id,
        domain="vpc",
        extra={
            "allocation_id": "eipalloc-123",
            "association_id": "eipassoc-456",
        },
    )

    aws_provider.driver.get_node.return_value = node_by_id
    aws_provider.driver.list_nodes.return_value = nodes
    aws_provider.driver.ex_describe_all_addresses.return_value = [address]
    aws_provider.driver.ex_disassociate_address.return_value = True
    aws_provider.driver.ex_release_address.return_value = True
    aws_provider._is_managed_elastic_ip = MagicMock(return_value=True)

    assert aws_provider.release_floating_ip(identifier) is True

    aws_provider.driver.ex_disassociate_address.assert_called_once_with(
        elastic_ip=address,
        domain="vpc",
    )
    aws_provider.driver.ex_release_address.assert_called_once_with(
        elastic_ip=address,
        domain="vpc",
    )
