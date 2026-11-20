"""Test‑wide fixtures.

The only fixture we need for the synthetic IP utilities is a deterministic RNG
seed.  By seeding the ``random`` module used inside ``tests.utils.ip_synthetic``
with a constant value we guarantee that every CI run (and every developer run
that uses this fixture) sees the same sequence of fake IP addresses.  This makes
the test suite reproducible while preserving the original intent of generating
"different" IPs on each execution.
"""

import pytest
from tests.utils.ip_synthetic import seed_synthetic_rng


@pytest.fixture(autouse=True, scope="session")
def deterministic_ip_seed():
    """Seed the synthetic IP RNG once per test session.

    The value ``0`` is arbitrary – any constant works.  The fixture is marked
    ``autouse`` so users do not need to import it explicitly.
    """
    seed_synthetic_rng(0)
