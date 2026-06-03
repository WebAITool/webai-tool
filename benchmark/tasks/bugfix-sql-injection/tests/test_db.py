"""Tests for bugfix-sql-injection task."""
import pytest
from db import UserDB


@pytest.fixture
def db():
    database = UserDB()
    yield database
    database.close()


def test_add_and_get_user(db):
    db.add_user("alice", "pass123", "alice@example.com")
    user = db.get_user("alice")
    assert user is not None
    assert user["username"] == "alice"
    assert user["email"] == "alice@example.com"


def test_verify_user_correct_password(db):
    db.add_user("bob", "secret", "bob@test.com")
    assert db.verify_user("bob", "secret") is True


def test_verify_user_wrong_password(db):
    db.add_user("carol", "mypass", "carol@test.com")
    assert db.verify_user("carol", "wrongpass") is False


def test_delete_user(db):
    db.add_user("dave", "pw", "dave@test.com")
    assert db.delete_user("dave") is True
    assert db.get_user("dave") is None


def test_list_users(db):
    db.add_user("e1", "p1")
    db.add_user("e2", "p2")
    users = db.list_users()
    assert len(users) == 2


def test_sql_injection_username_bypass(db):
    """Injection like admin' -- should NOT bypass auth."""
    db.add_user("admin", "realpassword", "admin@test.com")
    # This injection should NOT succeed
    result = db.verify_user("admin' --", "anything")
    assert result is False, "SQL injection bypassed authentication!"


def test_sql_injection_drop_table(db):
    """Injection in username should not drop the table."""
    db.add_user("normal", "pass")
    try:
        db.add_user("'; DROP TABLE users; --", "hack")
    except Exception:
        pass  # Expected: injection should fail
    # Table should still exist
    users = db.list_users()
    assert len(users) >= 1, "Table was dropped by injection!"


def test_sql_injection_union(db):
    """UNION-based injection should not leak data."""
    db.add_user("user1", "secret123", "private@email.com")
    user = db.get_user("' UNION SELECT 1,1,1,1 --")
    # Should return None, not a fake row
    assert user is None or user["username"] != "1", "UNION injection leaked data!"
