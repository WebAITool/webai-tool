import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, User, get_user_by_email, get_active_users, search_users, count_active_users


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    sess = Session()

    user1 = User(username="alice", email="alice@test.com", active=True)
    user2 = User(username="bob", email="bob@test.com", active=False)
    user3 = User(username="charlie", email="charlie@test.com", active=True)
    sess.add_all([user1, user2, user3])
    sess.commit()
    return sess


def test_get_user_by_email_finds_user(db):
    user = get_user_by_email("alice@test.com")
    assert user is not None
    assert user.username == "alice"


def test_get_user_by_email_returns_none(db):
    user = get_user_by_email("nonexistent@test.com")
    assert user is None


def test_get_active_users_returns_only_active(db):
    users = get_active_users()
    assert len(users) == 2
    assert all(u.active for u in users)


def test_count_active_users(db):
    count = count_active_users()
    assert count == 2


def test_search_users_returns_matching(db):
    users = search_users("ali")
    assert len(users) == 1
    assert users[0].username == "alice"