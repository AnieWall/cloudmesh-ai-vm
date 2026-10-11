import pytest
from cloudmesh.ai.vm.oracle.OracleManager import OracleManager
from tests.matrix.base import MatrixTestBase

class TestOracleMatrix(MatrixTestBase):
    def test_capabilities(self):
        config = {"clouds": {"oracle": {}}}
        self.__init__(OracleManager, config)
        results = self.probe_all()
        assert isinstance(results, dict)
