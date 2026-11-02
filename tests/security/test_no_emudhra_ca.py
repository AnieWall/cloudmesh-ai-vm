"""Security sanity‑check for the eMudhra intermediate certificate.

This test ensures that the `certifi` CA bundle shipped with the Python
environment does **not** contain the compromised eMudhra intermediate CA
and that the host's default OpenSSL trust store also does not trust it.

The test is derived from the recommendation in GitHub issue #112:
https://github.com/cloudmesh-ai/cloudmesh-ai-vm/issues/112.

If a reference to "eMudhra" is found the test will fail, prompting the
user to clean their system trust store (e.g., via `update-ca-certificates`
or `security delete-certificate` on macOS).  The test runs automatically
as part of the repo's existing `pytest -q` CI step because it lives under
the ``tests/`` directory.
"""

from pathlib import Path
import ssl

import certifi


def _assert_no_emudhra_in_text(text: str) -> None:
    """Assert that the string ``eMudhra`` does not appear in *text*.

    The comparison is case‑sensitive because the compromised authority is
    always capitalised exactly as "eMudhra" in the advisory.
    """
    if "eMudhra" in text:
        raise AssertionError("❌ eMudhra CA still present in trust store")


def test_certifi_bundle_is_clean() -> None:
    """Verify that the `certifi` bundle does not contain the eMudhra CA.

    ``certifi.where()`` returns the absolute path to the PEM file that
    contains a concatenated list of trusted certificates.  We read the
    file as UTF‑8 text and scan for the identifier.
    """
    bundle_path = Path(certifi.where())
    # ``certifi.where()`` should always point to an existing file.
    content = bundle_path.read_text(encoding="utf-8")
    _assert_no_emudhra_in_text(content)


def test_system_openssl_store_is_clean() -> None:
    """Check the system OpenSSL default context for the eMudhra CA.

    ``ssl.create_default_context()`` builds a context based on the host's
    trusted certificate store.  ``ctx.get_ca_certs()`` returns a list of
    dictionaries; each dictionary contains an ``issuer`` entry that can be
    inspected as a string.  We ensure none of the issuers mention
    ``eMudhra``.
    """
    ctx = ssl.create_default_context()
    for cert_dict in ctx.get_ca_certs():
        # ``issuer`` may be a tuple of tuples; converting to ``str`` gives a
        # readable representation suitable for a simple substring check.
        issuer = cert_dict.get("issuer", "")
        _assert_no_emudhra_in_text(str(issuer))

    # If we reach this point the system store is clean.
    assert True
