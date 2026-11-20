import click
import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from click.testing import CliRunner

from cloudmesh.ai.command.vm.doctor import doctor


def make_provider(
    requirements=True,
    validation=None,
    info=None,
):
    """Create a lightweight fake provider for doctor tests."""
    provider = SimpleNamespace()

    provider.cloud_name = "test-cloud"

    provider.check_requirements = MagicMock(
        return_value=requirements
    )

    provider.validate_config = MagicMock(
        return_value={} if validation is None else validation
    )

    provider.get_provider_info = MagicMock(
        return_value=(
            {"provider": "Test Provider"}
            if info is None
            else info
        )
    )

    return provider


def get_rows(mock_render):
    """Return the rows passed to render_table()."""
    return mock_render.call_args.args[2]

def find_row(rows, label):
    """Utility: locate a row by its first column (check label)."""
    for r in rows:
        if r[0] == label:
            return r
    return None
def get_rows(mock_render):
    """Return the rows passed to render_table()."""
    return mock_render.call_args.args[2]


def test_doctor_healthy_provider():
    provider = make_provider()

    runner = CliRunner()

    with patch(
        "cloudmesh.ai.command.vm.doctor.get_active_provider",
        return_value=provider,
    ), patch(
        "cloudmesh.ai.command.vm.doctor.render_table"
    ) as mock_render:
        result = runner.invoke(doctor, [])

    assert result.exit_code == 0

    provider.check_requirements.assert_called_once()
    provider.validate_config.assert_called_once()
    provider.get_provider_info.assert_called_once()

    rows = get_rows(mock_render)

    # The doctor command now adds a few extra rows (configuration file and version).
    # Verify that the core checks are present and all PASS.
    assert find_row(rows, "Provider") is not None
    assert find_row(rows, "Requirements") is not None
    assert find_row(rows, "Configuration") is not None
    assert find_row(rows, "Provider Info") is not None
    for label in ["Provider", "Requirements", "Configuration", "Provider Info"]:
        row = find_row(rows, label)
        assert row is not None
        assert "PASS" in row[1]


def test_doctor_skips_provider_info_when_requirements_fail():
    provider = make_provider(
        requirements=False
    )

    runner = CliRunner()

    with patch(
        "cloudmesh.ai.command.vm.doctor.get_active_provider",
        return_value=provider,
    ), patch(
        "cloudmesh.ai.command.vm.doctor.render_table"
    ) as mock_render:
        result = runner.invoke(doctor, [])

    assert result.exit_code == 0

    provider.check_requirements.assert_called_once()
    provider.validate_config.assert_called_once()
    provider.get_provider_info.assert_not_called()

    rows = get_rows(mock_render)
    requirements_row = find_row(rows, "Requirements")
    provider_info_row = find_row(rows, "Provider Info")

    assert requirements_row is not None
    assert requirements_row[0] == "Requirements"
    assert "FAIL" in requirements_row[1]

    assert provider_info_row is not None
    assert provider_info_row[0] == "Provider Info"
    assert "SKIP" in provider_info_row[1]


def test_doctor_detects_configuration_errors():
    provider = make_provider(
        requirements=True,
        validation={
            "errors": [
                "Missing image",
                "Missing credentials",
            ]
        },
    )

    runner = CliRunner()

    with patch(
        "cloudmesh.ai.command.vm.doctor.get_active_provider",
        return_value=provider,
    ), patch(
        "cloudmesh.ai.command.vm.doctor.render_table"
    ) as mock_render:
        result = runner.invoke(doctor, [])

    assert result.exit_code == 0

    rows = get_rows(mock_render)
    configuration_row = find_row(rows, "Configuration")
    assert configuration_row is not None
    assert configuration_row[0] == "Configuration"
    assert "FAIL" in configuration_row[1]
    assert "Missing image" in configuration_row[2]
    assert "Missing credentials" in configuration_row[2]


def test_doctor_handles_provider_info_failure():
    provider = make_provider(
        requirements=True,
        validation={},
    )

    provider.get_provider_info.side_effect = RuntimeError(
        "provider information unavailable"
    )

    runner = CliRunner()

    with patch(
        "cloudmesh.ai.command.vm.doctor.get_active_provider",
        return_value=provider,
    ), patch(
        "cloudmesh.ai.command.vm.doctor.render_table"
    ) as mock_render:
        result = runner.invoke(doctor, [])

    assert result.exit_code == 0

    rows = get_rows(mock_render)
    provider_info_row = find_row(rows, "Provider Info")
    assert provider_info_row is not None
    assert provider_info_row[0] == "Provider Info"
    assert "FAIL" in provider_info_row[1]
    assert (
        "provider information unavailable"
        in provider_info_row[2]
    )


def test_doctor_strict_returns_nonzero_on_failure():
    provider = make_provider(
        requirements=False
    )

    runner = CliRunner()

    with patch(
        "cloudmesh.ai.command.vm.doctor.get_active_provider",
        return_value=provider,
    ), patch(
        "cloudmesh.ai.command.vm.doctor.render_table"
    ):
        result = runner.invoke(
            doctor,
            ["--strict"],
        )

    assert result.exit_code == 1

    provider.get_provider_info.assert_not_called()

    # Click's intentional exit must not be converted into
    # "Unexpected Error" by handle_errors.
    assert "Unexpected Error" not in result.output
    assert "Aborted!" not in result.output


def test_doctor_json_output():
    """Verify that the ``--json`` flag produces a valid JSON document containing the core checks."""
    provider = make_provider()

    runner = CliRunner()

    with patch(
        "cloudmesh.ai.command.vm.doctor.get_active_provider",
        return_value=provider,
    ), patch(
        "cloudmesh.ai.command.vm.doctor.render_table"
    ) as mock_render:
        # ``--json`` forces JSON output; render_table should not be called.
        result = runner.invoke(doctor, ["--json"])

    assert result.exit_code == 0
    # The output should be valid JSON
    data = json.loads(result.output)
    # Basic sanity checks
    assert data["cloud"] == "test-cloud"
    assert data["failures"] == 0
    # The core checks must be present in the ``checks`` list.
    labels = {c["check"] for c in data["checks"]}
    for label in ["Provider", "Requirements", "Configuration", "Provider Info"]:
        assert label in labels
    # Ensure the table rendering was skipped.
    mock_render.assert_not_called()
