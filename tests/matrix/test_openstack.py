import pytest
from cloudmesh.ai.vm.openstack.OpenstackManager import OpenstackManager
from tests.matrix.base import MatrixTestBase

class TestOpenstackMatrix(MatrixTestBase):
    def test_capabilities(self):
        config = {"clouds": {"openstack": {}}}
        self.__init__(OpenstackManager, config)
        results = self.probe_all()
        assert isinstance(results, dict)
