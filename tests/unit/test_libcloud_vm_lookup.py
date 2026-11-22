"""Tests for the LibcloudManager.get_vm name‑first lookup logic.

The goal of these tests is to verify that when a lookup string matches both a VM
name and a different VM's ID, the implementation prefers the VM with the matching
name. This aligns with the desired "name‑wins" contract.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from cloudmesh.ai.vm.LibcloudManager import LibcloudManager


class DummyProvider(LibcloudManager):
    """A minimal concrete subclass of :class:`LibcloudManager` for testing.

    It stores the provided mock driver in ``self._driver`` *before* calling the
    base ``__init__``. The overridden ``_get_driver`` method then returns this
    stored driver, allowing the base class to initialise ``self.driver`` correctly.
    """

    def __init__(self, driver):
        # Store the driver so that ``_get_driver`` can return it during ``super``
        # initialisation.
        self._driver = driver
        # Initialise the LibcloudManager base class. This will call ``_get_driver``
        # which now returns ``self._driver``.
        super().__init__(config={}, cloud_name="test")

    def _get_driver(self):  # pragma: no cover – simple accessor
        return self._driver


def make_node(name: str, node_id: str):
    """Utility to create a simple node object with ``name`` and ``id`` attributes.

    ``SimpleNamespace`` is used for lightweight attribute storage.
    """
    return SimpleNamespace(name=name, id=node_id, state="running", public_ips=[])


@pytest.fixture
def mock_driver():
    """Provides a mock libcloud driver with configurable return values."""
    driver = MagicMock()
    # By default, the driver does not resolve a node via ``get_node``.
    driver.get_node.return_value = None
    return driver


def test_exact_name_has_priority_over_id(mock_driver):
    """Name match should win even when another node's ID matches the same string.

    The driver returns two nodes: one with a matching name and another with a
    matching ID. The expected result is the node whose ``name`` matches.
    """
    conflict_name = "conflict"
    # Node where name matches ``conflict``.
    node_by_name = make_node(name=conflict_name, node_id="nodeA-id")
    # Node where ID matches ``conflict``.
    node_by_id = make_node(name="other", node_id=conflict_name)
    # Return nodes in name‑first order.
    mock_driver.list_nodes.return_value = [node_by_name, node_by_id]

    provider = DummyProvider(mock_driver)
    result = provider.get_vm(conflict_name)
    assert result is node_by_name


def test_exact_name_has_priority_with_reversed_order(mock_driver):
    """Name match should win regardless of the order of nodes returned.

    The driver returns the same two nodes as the previous test but in reverse
    order, ensuring that the algorithm does not depend on list ordering.
    """
    conflict_name = "conflict"
    node_by_name = make_node(name=conflict_name, node_id="nodeA-id")
    node_by_id = make_node(name="other", node_id=conflict_name)
    # Return nodes in reverse order.
    mock_driver.list_nodes.return_value = [node_by_id, node_by_name]

    provider = DummyProvider(mock_driver)
    result = provider.get_vm(conflict_name)
    assert result is node_by_name


def test_exact_name_wins_over_native_get_node_id_match(mock_driver):
    """An ID match from get_node must not override an exact name match."""
    conflict = "vm-123"
    node_by_name = make_node(name=conflict, node_id="nodeA-id")
    node_by_id = make_node(name="production", node_id=conflict)

    mock_driver.get_node.return_value = node_by_id
    mock_driver.list_nodes.return_value = [node_by_id, node_by_name]

    provider = DummyProvider(mock_driver)

    assert provider.get_vm(conflict) is node_by_name


def test_id_fallback_when_no_name_matches(mock_driver):
    """ID lookup should work when no exact name exists."""
    node_by_id = make_node(name="production", node_id="vm-123")
    mock_driver.get_node.return_value = None
    mock_driver.list_nodes.return_value = [node_by_id]

    provider = DummyProvider(mock_driver)

    assert provider.get_vm("vm-123") is node_by_id


def test_native_lookup_fallback_without_list_nodes():
    """Support drivers that expose get_node but not list_nodes."""
    driver = MagicMock(spec=["get_node"])
    node = make_node(name="production", node_id="vm-123")
    driver.get_node.return_value = node

    provider = DummyProvider(driver)

    assert provider.get_vm("vm-123") is node
