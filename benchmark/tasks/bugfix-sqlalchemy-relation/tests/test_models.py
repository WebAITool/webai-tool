"""Tests for bugfix-sqlalchemy-relation task."""
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from models import Base, User, Post


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    # Enable foreign keys for SQLite
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    sess = Session()
    yield sess
    sess.close()


def test_create_user_with_posts(session):
    user = User(username="alice", email="alice@test.com")
    session.add(user)
    session.commit()

    post1 = Post(title="First", content="Hello", user_id=user.id)
    post2 = Post(title="Second", content="World", user_id=user.id)
    session.add_all([post1, post2])
    session.commit()

    assert len(user.posts) == 2


def test_to_dict_user(session):
    user = User(username="bob", email="bob@test.com")
    session.add(user)
    session.commit()
    d = user.to_dict()
    assert d["username"] == "bob"
    assert d["email"] == "bob@test.com"


def test_to_dict_post(session):
    user = User(username="carol", email="carol@test.com")
    session.add(user)
    session.commit()
    post = Post(title="Test", content="x", user_id=user.id)
    session.add(post)
    session.commit()
    d = post.to_dict()
    assert d["title"] == "Test"
    assert d["user_id"] == user.id


def test_cascade_delete_removes_posts(session):
    """Deleting a user should cascade-delete their posts."""
    user = User(username="dave", email="dave@test.com")
    session.add(user)
    session.commit()

    post1 = Post(title="P1", content="a", user_id=user.id)
    post2 = Post(title="P2", content="b", user_id=user.id)
    session.add_all([post1, post2])
    session.commit()

    user_id = user.id
    session.delete(user)
    session.commit()

    # Posts should be gone
    remaining = session.query(Post).filter(Post.user_id == user_id).all()
    assert len(remaining) == 0, f"Expected 0 orphaned posts, found {len(remaining)}"


def test_no_orphaned_posts_after_delete(session):
    """Posts should not become orphaned (user_id=NULL) after user delete."""
    user = User(username="eve", email="eve@test.com")
    session.add(user)
    session.commit()

    post = Post(title="Orphan", content="test", user_id=user.id)
    session.add(post)
    session.commit()

    session.delete(user)
    session.commit()

    orphans = session.query(Post).filter(Post.user_id == None).all()
    assert len(orphans) == 0, f"Found {len(orphans)} orphaned posts with user_id=NULL"


def test_delete_one_user_does_not_affect_another(session):
    """Deleting user A should not affect user B's posts."""
    user_a = User(username="alice2", email="a2@test.com")
    user_b = User(username="bob2", email="b2@test.com")
    session.add_all([user_a, user_b])
    session.commit()

    post_a = Post(title="A post", content="a", user_id=user_a.id)
    post_b = Post(title="B post", content="b", user_id=user_b.id)
    session.add_all([post_a, post_b])
    session.commit()

    session.delete(user_a)
    session.commit()

    # User B's post should still exist
    assert session.query(Post).filter(Post.user_id == user_b.id).count() == 1
