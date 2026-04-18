"""Tests for PasswordManager — SL-1 (passlib → argon2-cffi migration).

Test contract:
  - hash_password returns an argon2id hash ($argon2id$ prefix)
  - verify_password accepts an argon2 hash (returns bool)
  - verify_password accepts a legacy bcrypt hash and rehashes on match
    (returns tuple[bool, str] where str is a new $argon2id$ hash)
  - verify_password rejects a wrong password for both hash types (returns False)
"""

import pytest

from mcp_server.security.auth_manager import PasswordManager


# ---------------------------------------------------------------------------
# Fixtures / constants
# ---------------------------------------------------------------------------

# A pre-generated legacy $2b$ bcrypt hash of 'testpw' (generated with bcrypt 4.x).
# Hardcoded so the test does NOT depend on bcrypt hash-generation behaviour at
# test-run time; only the *verification* path is exercised.
LEGACY_BCRYPT_HASH = "$2b$12$mWD/c4F17E0iGRFYCaWvx.T.1Rk9k9TVRH0PU3x139u7n2l4X8upS"
LEGACY_BCRYPT_PASSWORD = "testpw"


@pytest.fixture
def pm() -> PasswordManager:
    return PasswordManager()


# ---------------------------------------------------------------------------
# SL-1.1-a: hash_password returns an argon2id hash
# ---------------------------------------------------------------------------


def test_hash_password_returns_argon2id(pm: PasswordManager) -> None:
    """hash_password must produce a $argon2id$ hash."""
    h = pm.hash_password("somepassword")
    assert h.startswith("$argon2id$"), (
        f"Expected argon2id hash prefix, got: {h!r}"
    )


# ---------------------------------------------------------------------------
# SL-1.1-b: verify_password accepts a native argon2 hash
# ---------------------------------------------------------------------------


def test_verify_password_accepts_argon2_hash_correct(pm: PasswordManager) -> None:
    """verify_password returns True for a correct argon2 hash."""
    plain = "correcthorsebatterystaple"
    h = pm.hash_password(plain)
    result = pm.verify_password(plain, h)
    assert result is True


def test_verify_password_rejects_argon2_hash_wrong_password(pm: PasswordManager) -> None:
    """verify_password returns False for a wrong password against an argon2 hash."""
    h = pm.hash_password("rightpassword")
    result = pm.verify_password("wrongpassword", h)
    assert result is False


# ---------------------------------------------------------------------------
# SL-1.1-c: verify_password accepts a legacy bcrypt hash and rehashes on match
# ---------------------------------------------------------------------------


def test_verify_password_accepts_legacy_bcrypt_correct(pm: PasswordManager) -> None:
    """verify_password returns (True, new_argon2_hash) for a correct legacy bcrypt hash."""
    result = pm.verify_password(LEGACY_BCRYPT_PASSWORD, LEGACY_BCRYPT_HASH)
    assert isinstance(result, tuple), (
        "Expected tuple[bool, str] for bcrypt match, got plain bool"
    )
    ok, new_hash = result
    assert ok is True
    assert new_hash.startswith("$argon2id$"), (
        f"Rehashed value should be argon2id, got: {new_hash!r}"
    )


def test_verify_password_rehash_is_valid_argon2(pm: PasswordManager) -> None:
    """The rehashed argon2 hash produced from a bcrypt match must itself verify correctly."""
    _, new_hash = pm.verify_password(LEGACY_BCRYPT_PASSWORD, LEGACY_BCRYPT_HASH)  # type: ignore[misc]
    # Round-trip: the newly minted argon2 hash must accept the same plain password
    assert pm.verify_password(LEGACY_BCRYPT_PASSWORD, new_hash) is True


def test_verify_password_rejects_legacy_bcrypt_wrong_password(pm: PasswordManager) -> None:
    """verify_password returns False for a wrong password against a legacy bcrypt hash."""
    result = pm.verify_password("wrongpassword", LEGACY_BCRYPT_HASH)
    assert result is False


# ---------------------------------------------------------------------------
# SL-1.1-d: legacy $2a$ variant is also handled
# ---------------------------------------------------------------------------


def test_verify_password_handles_2a_prefix(pm: PasswordManager) -> None:
    """A hash starting with $2a$ should be treated the same as $2b$."""
    # $2a$ and $2b$ are interchangeable for bcrypt; bcrypt.checkpw handles both.
    # We build a $2a$ hash by replacing the prefix of our known hash.
    hash_2a = "$2a$" + LEGACY_BCRYPT_HASH[4:]
    result = pm.verify_password(LEGACY_BCRYPT_PASSWORD, hash_2a)
    assert isinstance(result, tuple), (
        "Expected tuple[bool, str] for $2a$ bcrypt match"
    )
    ok, new_hash = result
    assert ok is True
    assert new_hash.startswith("$argon2id$")
