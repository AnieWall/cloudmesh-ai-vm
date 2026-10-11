import pytest
from cloudmesh.ai.vm.local.LimaManager import LimaManager
from tests.matrix.base import MatrixTestBase

class TestLimaMatrix(MatrixTestBase):
    def test_capabilities(self):
        config = {"clouds": {"lima": {}}}
        self.__init__(LimaManager, config)
        results = self.probe_all()
        assert isinstance(results, dict)
