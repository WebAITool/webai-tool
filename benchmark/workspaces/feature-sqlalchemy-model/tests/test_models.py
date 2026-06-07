"""Tests for feature-sqlalchemy-model task."""
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from models import Base, User, Post


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
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


def test_project_model_exists(session):
    """Project model should be importable."""
    from models import Project
    assert Project is not None


def test_task_model_exists(session):
    """Task model should be importable."""
    from models import Task
    assert Task is not None


def test_create_project(session):
    from models import Project
    user = User(username="owner", email="o@test.com")
    session.add(user)
    session.commit()

    project = Project(name="WebApp", description="A project", owner_id=user.id)
    session.add(project)
    session.commit()

    assert project.id is not None
    assert project.name == "WebApp"
    assert project.status == "active"


def test_project_to_dict(session):
    from models import Project
    user = User(username="owner2", email="o2@test.com")
    session.add(user)
    session.commit()

    project = Project(name="API", owner_id=user.id)
    session.add(project)
    session.commit()

    d = project.to_dict()
    assert "id" in d
    assert d["name"] == "API"
    assert d["status"] == "active"
    assert "owner_id" in d


def test_create_task(session):
    from models import Project, Task
    user = User(username="dev", email="d@test.com")
    session.add(user)
    session.commit()

    project = Project(name="Sprint1", owner_id=user.id)
    session.add(project)
    session.commit()

    task = Task(title="Fix bug", project_id=project.id, assignee_id=user.id)
    session.add(task)
    session.commit()

    assert task.id is not None
    assert task.status == "todo"
    assert task.priority == "medium"


def test_task_to_dict(session):
    from models import Project, Task
    user = User(username="dev2", email="d2@test.com")
    session.add(user)
    session.commit()

    project = Project(name="Sprint2", owner_id=user.id)
    session.add(project)
    session.commit()

    task = Task(title="Implement feature", project_id=project.id)
    session.add(task)
    session.commit()

    d = task.to_dict()
    assert "id" in d
    assert d["title"] == "Implement feature"
    assert d["status"] == "todo"
    assert d["priority"] == "medium"


def test_project_cascade_deletes_tasks(session):
    from models import Project, Task
    user = User(username="cascade", email="c@test.com")
    session.add(user)
    session.commit()

    project = Project(name="DeleteMe", owner_id=user.id)
    session.add(project)
    session.commit()

    task = Task(title="Orphan", project_id=project.id)
    session.add(task)
    session.commit()

    session.delete(project)
    session.commit()

    remaining = session.query(Task).filter(Task.project_id == project.id).all()
    assert len(remaining) == 0


def test_user_has_projects_relationship(session):
    from models import Project
    user = User(username="pm", email="pm@test.com")
    session.add(user)
    session.commit()

    project = Project(name="MyProject", owner_id=user.id)
    session.add(project)
    session.commit()

    assert hasattr(user, "projects")
    assert len(user.projects) == 1


def test_user_has_assigned_tasks(session):
    from models import Project, Task
    user = User(username="assignee", email="a@test.com")
    session.add(user)
    session.commit()

    project = Project(name="Proj", owner_id=user.id)
    session.add(project)
    session.commit()

    task = Task(title="Do this", project_id=project.id, assignee_id=user.id)
    session.add(task)
    session.commit()

    assert hasattr(user, "assigned_tasks")
    assert len(user.assigned_tasks) == 1


def test_existing_models_still_work(session):
    """User and Post should still work after adding new models."""
    user = User(username="legacy", email="l@test.com")
    session.add(user)
    session.commit()

    post = Post(title="Old post", content="still works", user_id=user.id)
    session.add(post)
    session.commit()

    assert len(user.posts) == 1
    assert user.to_dict()["username"] == "legacy"
