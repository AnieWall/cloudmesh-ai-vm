import pytest
from typing import Any, Callable
from cloudmesh.ai.vm.exceptions import ProviderFeatureNotSupported

class ComplianceHelper:
    """
    Helper class for provider compliance tests.
    Provides utilities for feature guarding and standardized assertions.
    """

    @staticmethod
    def ensure_supported(func: Callable, *args, **kwargs) -> Any:
        """
        Wraps a provider method call.
        If ProviderFeatureNotSupported is raised, marks the test as skipped.
        """
        try:
            return func(*args, **kwargs)
        except ProviderFeatureNotSupported:
            pytest.skip("Provider does not support this feature")

    @staticmethod
    def assert_is_list_of_dicts(result: Any, item_key: str = "name"):
        """
        Ensures the result is a list of dictionaries and each dict contains the expected key.
        """
        assert isinstance(result, list), f"Expected list, got {type(result)}"
        for item in result:
            assert isinstance(item, dict), f"Expected list item to be dict, got {type(item)}"
            assert item_key in item, f"Expected dict item to contain key '{item_key}'"
