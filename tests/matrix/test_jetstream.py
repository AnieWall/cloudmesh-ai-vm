import pytest
from cloudmesh.ai.vm.openstack.JetstreamManager import JetstreamManager
from tests.matrix.base import MatrixTestBase

class TestJetstreamMatrix(MatrixTestBase):
    def test_capabilities(self):
        config = {"clouds": {"jetstream": {}}}
        self.__init__(JetstreamManager, config)
        results = self.probe_all()
        assert isinstance(results, dict)
