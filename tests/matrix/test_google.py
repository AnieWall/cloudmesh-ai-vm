import pytest
from cloudmesh.ai.vm.google.GoogleManager import GoogleManager
from tests.matrix.base import MatrixTestBase

class TestGoogleMatrix(MatrixTestBase):
    def test_capabilities(self):
        config = {"clouds": {"google": {}}}
        self.__init__(GoogleManager, config)
        results = self.probe_all()
        assert isinstance(results, dict)
