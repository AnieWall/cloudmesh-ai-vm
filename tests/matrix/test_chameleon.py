import pytest
from cloudmesh.ai.vm.openstack.ChameleonManager import ChameleonManager
from tests.matrix.base import MatrixTestBase

class TestChameleonMatrix(MatrixTestBase):
    def test_capabilities(self):
        config = {"clouds": {"chameleon": {}}}
        self.__init__(ChameleonManager, config)
        results = self.probe_all()
        assert isinstance(results, dict)
