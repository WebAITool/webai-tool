"""Tests for bugfix-pydantic-schema task."""
import pytest
from datetime import datetime
from pydantic import ValidationError
from schemas import UserCreate, UserResponse, ItemCreate, ItemResponse


def test_username_min_length():
    """Username must be at least 3 characters."""
    with pytest.raises(ValidationError):
        UserCreate(username="ab", email="a@b.com", password="secret")

    # Valid username should work
    user = UserCreate(username="alice", email="a@b.com", password="secret")
    assert user.username == "alice"


def test_email_validation():
    """Email must be a valid email address."""
    with pytest.raises(ValidationError):
        UserCreate(username="alice", email="not-an-email", password="secret")

    # Valid email should work
    user = UserCreate(username="alice", email="alice@example.com", password="secret")
    assert user.email == "alice@example.com"


def test_price_non_negative():
    """Price must be >= 0."""
    with pytest.raises(ValidationError):
        ItemCreate(name="Widget", price=-5.0)

    # Zero price should be valid
    item = ItemCreate(name="Free", price=0)
    assert item.price == 0

    # Positive price should work
    item = ItemCreate(name="Paid", price=9.99)
    assert item.price == 9.99


def test_user_response_excludes_password_hash():
    """UserResponse should NOT contain password_hash."""
    resp = UserResponse(id=1, username="alice", email="a@b.com", password_hash="$2b$12$xxx")
    data = resp.model_dump()
    assert "password_hash" not in data, f"password_hash leaked in response: {data.keys()}"


def test_item_response_has_created_at():
    """ItemResponse should include created_at field."""
    now = datetime.now()
    resp = ItemResponse(id=1, name="Widget", price=9.99, description="test", created_at=now)
    data = resp.model_dump()
    assert "created_at" in data, "created_at missing from ItemResponse"


def test_valid_user_create():
    """Valid UserCreate should still work."""
    user = UserCreate(username="bob", email="bob@test.com", password="mypass123")
    assert user.username == "bob"


def test_valid_item_create():
    """Valid ItemCreate should still work."""
    item = ItemCreate(name="Book", price=19.99, description="A good book")
    assert item.name == "Book"
