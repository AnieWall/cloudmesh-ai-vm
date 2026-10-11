import pytest
from cloudmesh.ai.vm.aws.AwsManager import AwsManager
from tests.matrix.base import MatrixTestBase

class TestAwsMatrix(MatrixTestBase):
    def test_capabilities(self):
        # Use a mock config for probing
        config = {"clouds": {"aws": {"region": "us-east-1"}}}
        self.__init__(AwsManager, config)
        results = self.probe_all()
        # We can use a fixture or a global store to collect results
        # For now, we just ensure they are computed.
        # The report script will instantiate these and run probe_all().
        assert isinstance(results, dict)
