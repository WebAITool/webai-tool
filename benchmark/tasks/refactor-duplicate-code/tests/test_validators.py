"""Tests for refactor-duplicate-code task.

These tests verify that:
1. All existing validators still work exactly as before
2. A new validate_username() function exists and works
3. The code uses a Validator base class (structural check)

Run: pytest tests/ -v
"""
import pytest
import inspect


def _import_validators():
    import validators
    return validators


def test_validate_name_valid():
    v = _import_validators()
    assert v.validate_name("Alice") == "Alice"


def test_validate_name_none():
    v = _import_validators()
    with pytest.raises(ValueError, match="name is required"):
        v.validate_name(None)


def test_validate_name_too_short():
    v = _import_validators()
    with pytest.raises(ValueError, match="at least 2"):
        v.validate_name("A")


def test_name_type_error():
    v = _import_validators()
    with pytest.raises(TypeError, match="must be a string"):
        v.validate_name(123)


def test_validate_email_valid():
    v = _import_validators()
    assert v.validate_email("user@example.com") == "user@example.com"


def test_validate_email_invalid_format():
    v = _import_validators()
    with pytest.raises(ValueError, match="email format"):
        v.validate_email("not-an-email")


def test_validate_email_none():
    v = _import_validators()
    with pytest.raises(ValueError, match="email is required"):
        v.validate_email(None)


def test_validate_age_valid():
    v = _import_validators()
    assert v.validate_age(25) == 25


def test_validate_age_negative():
    v = _import_validators()
    with pytest.raises(ValueError, match="at least 0"):
        v.validate_age(-1)


def test_validate_age_type_error():
    v = _import_validators()
    with pytest.raises(TypeError, match="must be an integer"):
        v.validate_age("25")


def test_validate_phone_valid():
    v = _import_validators()
    assert v.validate_phone("+7 999 123-45-67") == "+7 999 123-45-67"


def test_validate_phone_invalid_format():
    v = _import_validators()
    with pytest.raises(ValueError, match="phone format"):
        v.validate_phone("abc")


def test_validate_phone_none():
    v = _import_validators()
    with pytest.raises(ValueError, match="phone is required"):
        v.validate_phone(None)


def test_validate_username_exists():
    """New validate_username function should exist."""
    v = _import_validators()
    assert hasattr(v, "validate_username"), "validate_username() not found"


def test_validate_username_valid():
    """validate_username should accept valid usernames."""
    v = _import_validators()
    assert v.validate_username("alice123") == "alice123"


def test_validate_username_none():
    v = _import_validators()
    with pytest.raises(ValueError, match="username is required"):
        v.validate_username(None)


def test_validator_base_class_exists():
    """There should be a Validator base class in the module."""
    v = _import_validators()
    assert hasattr(v, "Validator"), "Validator base class not found"
    assert inspect.isclass(v.Validator), "Validator should be a class"
