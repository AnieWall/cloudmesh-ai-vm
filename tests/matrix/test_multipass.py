import pytest
from cloudmesh.ai.vm.local.MultipassManager import MultipassManager
from tests.matrix.base import MatrixTestBase

class TestMultipassMatrix(MatrixTestBase):
    def test_capabilities(self):
        config = {"clouds": {"multipass": {}}}
        self.__init__(MultipassManager, config)
        results = self.probe_all()
        assert isinstance(results, dict)
