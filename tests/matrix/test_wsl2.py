import pytest
from cloudmesh.ai.vm.local.Wsl2Manager import Wsl2Manager
from tests.matrix.base import MatrixTestBase

class TestWsl2Matrix(MatrixTestBase):
    def test_capabilities(self):
        config = {"clouds": {"wsl2": {}}}
        self.__init__(Wsl2Manager, config)
        results = self.probe_all()
        assert isinstance(results, dict)
