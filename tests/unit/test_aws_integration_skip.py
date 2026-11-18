"""Regression tests for AWS live integration-test safeguards."""

import importlib.util
from pathlib import Path

import pytest


INTEGRATION_DIR = Path(__file__).resolve().parents[1] / "integration"
CONFTEST_PATH = INTEGRATION_DIR / "conftest.py"

spec = importlib.util.spec_from_file_location(
    "aws_integration_conftest_under_test", CONFTEST_PATH
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

aws_live_provider = module.aws_live_provider.__wrapped__


def test_aws_live_test_disabled(monkeypatch):
    """Disabled live testing must skip before provider initialization."""
    monkeypatch.delenv("CLOUDMESH_AWS_LIVE_TEST", raising=False)

    with pytest.raises(
        pytest.skip.Exception,
        match="Live AWS lifecycle test disabled",
    ):
        aws_live_provider()


def test_aws_live_test_requires_explicit_config(monkeypatch):
    """Live testing requires an explicitly selected configuration file."""
    monkeypatch.setenv("CLOUDMESH_AWS_LIVE_TEST", "1")
    monkeypatch.delenv("CLOUDMESH_VM_CONFIG", raising=False)

    with pytest.raises(
        pytest.skip.Exception,
        match="CLOUDMESH_VM_CONFIG is required",
    ):
        aws_live_provider()


def test_aws_initialization_error_is_not_skipped(
    monkeypatch, tmp_path
):
    """Unexpected provider initialization errors must propagate."""
    config_file = tmp_path / "clouds.yaml"
    config_file.write_text(
        "clouds:\n"
        "  aws:\n"
        "    access_key: test-access\n"
        "    secret_key: test-secret\n"
        "    image: ami-test\n"
        "    flavor: t3.micro\n"
    )

    monkeypatch.setenv("CLOUDMESH_AWS_LIVE_TEST", "1")
    monkeypatch.setenv("CLOUDMESH_VM_CONFIG", str(config_file))

    from cloudmesh.ai.vm.aws.AwsManager import Provider

    def broken_initialization(self, config, **kwargs):
        raise TypeError("Unexpected AWS provider initialization error")

    monkeypatch.setattr(Provider, "__init__", broken_initialization)

    with pytest.raises(
        TypeError,
        match="Unexpected AWS provider initialization error",
    ):
        aws_live_provider()


def test_aws_live_test_skips_incomplete_config(monkeypatch, tmp_path):
    """Incomplete AWS configuration must skip before provider initialization."""
    config_file = tmp_path / "clouds.yaml"
    config_file.write_text(
        "clouds:\n"
        "  aws:\n"
        "    region: us-east-1\n"
    )

    monkeypatch.setenv("CLOUDMESH_AWS_LIVE_TEST", "1")
    monkeypatch.setenv("CLOUDMESH_VM_CONFIG", str(config_file))

    with pytest.raises(
        pytest.skip.Exception,
        match="AWS configuration incomplete",
    ):
        aws_live_provider()
