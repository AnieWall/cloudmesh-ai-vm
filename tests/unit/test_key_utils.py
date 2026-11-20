"""Unit tests for the ``cloudmesh.ai.vm.key_utils`` module.

These tests cover the full resolution logic for SSH public keys, ensuring that
the helper behaves correctly in the presence of explicit configuration as well
as fallback discovery from ``~/.ssh``.
"""

import os
import pathlib

import pytest

from cloudmesh.ai.vm.key_utils import resolve_key_path
from cloudmesh.ai.command._shared.exceptions import VMCommandError


def test_resolve_key_path_explicit(tmp_path):
    """Explicit ``key_path`` resolves correctly and derives the name from the filename."""
    key_file = tmp_path / "mykey.pub"
    key_file.write_text("ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQD... user@example.com")

    config = {"key_path": str(key_file)}
    path, name = resolve_key_path(config)

    assert path == key_file
    assert name == "mykey"


def test_resolve_key_path_explicit_with_name(tmp_path):
    """When ``key_name`` is provided it overrides the derived name."""
    key_file = tmp_path / "mykey.pub"
    key_file.write_text("ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQD... user@example.com")

    config = {"key_path": str(key_file), "key_name": "custom-name"}
    path, name = resolve_key_path(config)

    assert path == key_file
    assert name == "custom-name"


def test_resolve_key_path_missing_file(tmp_path):
    """An explicit ``key_path`` that does not exist raises ``VMCommandError``."""
    missing = tmp_path / "does-not-exist.pub"
    config = {"key_path": str(missing)}
    with pytest.raises(VMCommandError) as exc:
        resolve_key_path(config)
    assert "does not exist" in str(exc.value)


def test_resolve_key_path_default_single(tmp_path, monkeypatch):
    """When no ``key_path`` is set, a single ``*.pub`` file in ``~/.ssh`` is used."""
    ssh_dir = tmp_path / ".ssh"
    ssh_dir.mkdir()
    key_file = ssh_dir / "default.pub"
    key_file.write_text("ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQD... user@example.com")

    monkeypatch.setenv("HOME", str(tmp_path))
    config = {}
    path, name = resolve_key_path(config)

    assert path == key_file
    assert name == "default"


def test_resolve_key_path_default_multiple(tmp_path, monkeypatch):
    """Multiple ``*.pub`` files in ``~/.ssh`` cause an error, prompting the user to specify ``key_path``."""
    ssh_dir = tmp_path / ".ssh"
    ssh_dir.mkdir()
    (ssh_dir / "a.pub").write_text("ssh-rsa AAA... a")
    (ssh_dir / "b.pub").write_text("ssh-rsa AAA... b")

    monkeypatch.setenv("HOME", str(tmp_path))
    config = {}
    with pytest.raises(VMCommandError) as exc:
        resolve_key_path(config)
    # The error message should mention that multiple public keys were found.
    assert "multiple ssh public keys" in str(exc.value).lower()


def test_resolve_key_path_no_ssh_dir(tmp_path, monkeypatch):
    """If ``~/.ssh`` does not exist, a clear ``VMCommandError`` is raised."""
    # Ensure ``~/.ssh`` is absent.
    monkeypatch.setenv("HOME", str(tmp_path))
    config = {}
    with pytest.raises(VMCommandError) as exc:
        resolve_key_path(config)
    # The error message should indicate that the ``~/.ssh`` directory is missing.
    assert "ssh directory not found" in str(exc.value).lower()
