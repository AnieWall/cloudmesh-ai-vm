"""Stub ``libcloud.compute.types`` module.

Defines the ``Provider`` enumeration with the constants required by the test
suite and provider implementations.  Additional providers can be added later
without breaking existing code.
"""


class Provider:
    # Minimal set of provider constants used in the codebase.
    AZURE_ARM = "azure_arm"
    GCE = "gce"
    EC2 = "ec2"
    # The real libcloud library defines many more constants; they are omitted
    # here because they are not needed for the current test matrix.


class NodeState:
    """Simplified representation of node states used in tests.

    The real ``libcloud.compute.types.NodeState`` enum includes many states.
    For the unit tests only ``RUNNING``, ``STOPPED`` and ``PENDING`` are
    required, so we provide those as class attributes.
    """

    RUNNING = "running"
    STOPPED = "stopped"
    PENDING = "pending"
