import pytest
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from models import Base


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    try:
        Base.metadata.create_all(engine)
    except Exception:
        # SQLite cannot render TSVECTOR (PostgreSQL-only type)
        # Create table without the search_vector column for testing basic fields
        engine.execute("""
            CREATE TABLE documents (
                id INTEGER PRIMARY KEY,
                title VARCHAR(200) NOT NULL,
                content TEXT NOT NULL,
                category VARCHAR(50) DEFAULT 'general',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    Session = sessionmaker(bind=engine)
    sess = Session()
    yield sess
    sess.close()


def test_document_model_has_basic_fields(session):
    from models import Document
    doc = Document(title="Test Title", content="Test content here", category="tech")
    session.add(doc)
    session.commit()
    assert doc.id is not None
    assert doc.title == "Test Title"


def test_search_vector_column_exists():
    from models import Document
    if hasattr(Document, "search_vector"):
        col = Document.search_vector
        assert col is not None, "search_vector column should exist"
    else:
        has_sv = any(
            hasattr(Document, c) and "search" in c.lower()
            for c in dir(Document)
        )
        assert has_sv or hasattr(Document, "search_vector"), "search_vector column not found on Document"


def test_search_documents_function_exists():
    try:
        from models import search_documents
        assert callable(search_documents), "search_documents should be callable"
    except ImportError:
        assert False, "search_documents function not found in models.py"


def test_gin_index_exists():
    import ast
    source = Path(__file__).parent.parent / "models.py"
    tree = ast.parse(source.read_text(encoding="utf-8"))
    has_tsvector = False
    has_gin = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if "TSVECTOR" in ast.dump(node):
                has_tsvector = True
            if "gin" in ast.dump(node).lower():
                has_gin = True
    assert has_tsvector, "models.py should define a TSVECTOR search_vector column"
    assert has_gin, "models.py should define a GIN index on search_vector"