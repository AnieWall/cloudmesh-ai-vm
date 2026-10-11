import pytest
from cloudmesh.ai.vm.azure.AzureManager import AzureManager
from tests.matrix.base import MatrixTestBase

class TestAzureMatrix(MatrixTestBase):
    def test_capabilities(self):
        config = {"clouds": {"azure": {}}}
        self.__init__(AzureManager, config)
        results = self.probe_all()
        assert isinstance(results, dict)
