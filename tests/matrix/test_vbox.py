import pytest
from cloudmesh.ai.vm.local.VBoxManager import VBoxManager
from tests.matrix.base import MatrixTestBase

class TestVBoxMatrix(MatrixTestBase):
    def test_capabilities(self):
        config = {"clouds": {"vbox": {}}}
        self.__init__(VBoxManager, config)
        results = self.probe_all()
        assert isinstance(results, dict)
