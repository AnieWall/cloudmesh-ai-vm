"""Synthetic IP address generator for tests.

This module provides a tiny, deterministic (when seeded) helper that returns
non‑routable IPv4 addresses.  The intent is to avoid using real, public IPs in
unit‑tests, logs, rate‑limit checks, or any place where a network call could be
accidentally performed.

Supported modes:
* ``private``  – any address from the RFC1918 private ranges (10/8,
  172.16/12, 192.168/16).
* ``testnet`` – addresses from the officially reserved TEST‑NET blocks (192.0.2.0/24,
  198.51.100.0/24, 203.0.113.0/24).
* ``random``  – any IPv4 address **excluding** reserved, multicast, loop‑back,
  link‑local, and the two ranges above.  This approximates a fully random public
  address while still guaranteeing the tests never reach an actual host.

All functions raise ``ValueError`` for unsupported modes.  The RNG can be
seeded via :func:`seed_synthetic_rng` – a fixture in ``tests/conftest.py`` calls
this with a constant seed so CI runs are reproducible.
"""

from __future__ import annotations

import random
import ipaddress
from typing import Iterable, Tuple

# ---------------------------------------------------------------------------
# Pre‑defined address pools
# ---------------------------------------------------------------------------
PRIVATE_BLOCKS = [
    ipaddress.IPv4Network("10.0.0.0/8"),
    ipaddress.IPv4Network("172.16.0.0/12"),
    ipaddress.IPv4Network("192.168.0.0/16"),
]

TESTNET_BLOCKS = [
    ipaddress.IPv4Network("192.0.2.0/24"),
    ipaddress.IPv4Network("198.51.100.0/24"),
    ipaddress.IPv4Network("203.0.113.0/24"),
]


def _random_host_from(network: ipaddress.IPv4Network) -> str:
    """Return a random usable host address from *network* (excludes network & broadcast)."""
    hosts = tuple(network.hosts())
    if not hosts:
        raise ValueError(f"Network {network} has no usable hosts")
    return str(random.choice(hosts))


def _pick_from(pools: Iterable[ipaddress.IPv4Network]) -> str:
    """Randomly pick a pool, then a random host inside it."""
    pool = random.choice(list(pools))
    return _random_host_from(pool)


def synthetic_ip_pair(mode: str = "private") -> Tuple[str, str]:
    """Return ``(fixed_ip, floating_ip)`` according to *mode*.

    Parameters
    ----------
    mode:
        ``"private"`` – addresses from the RFC1918 private ranges.
        ``"testnet"`` – addresses from the IETF TEST‑NET blocks.
        ``"random"`` – any address that is not reserved, multicast, loop‑back,
        link‑local, or in the private/test‑net pools.
    """
    if mode == "private":
        pools = PRIVATE_BLOCKS
    elif mode == "testnet":
        pools = TESTNET_BLOCKS
    elif mode == "random":
        # Build a filtered view of the entire IPv4 space, excluding special ranges.
        excluded = (
            PRIVATE_BLOCKS
            + TESTNET_BLOCKS
            + [
                ipaddress.IPv4Network("127.0.0.0/8"),   # loop‑back
                ipaddress.IPv4Network("224.0.0.0/4"),   # multicast
                ipaddress.IPv4Network("169.254.0.0/16"),  # link‑local
                ipaddress.IPv4Network("240.0.0.0/4"),   # reserved/experimental
            ]
        )
        # ``0.0.0.0/0`` represents the whole IPv4 address space.
        all_space = ipaddress.IPv4Network("0.0.0.0/0")
        # Generate sub‑nets of size /8 and filter out any that are fully excluded.
        pools = [
            net
            for net in all_space.subnets(new_prefix=8)
            if not any(net.subnet_of(exc) for exc in excluded)
        ]
    else:
        raise ValueError(f"Unsupported synthetic‑IP mode: {mode!r}")

    # Choose two distinct addresses – extremely unlikely to clash, but we protect
    # against it for absolute safety.
    fixed = _pick_from(pools)
    floating = _pick_from(pools)
    while floating == fixed:
        floating = _pick_from(pools)
    return fixed, floating


def synthetic_ip(mode: str = "private") -> str:
    """Convenient wrapper when only a single address is required."""
    return synthetic_ip_pair(mode)[0]


def seed_synthetic_rng(seed: int = 0) -> None:
    """Seed the internal ``random`` module.

    Call this once (e.g. from a ``pytest`` fixture) to obtain reproducible
    sequences of synthetic IPs across CI runs.
    """
    random.seed(seed)
