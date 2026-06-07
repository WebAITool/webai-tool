import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    sess = Session()
    yield sess
    sess.close()


def test_product_model_has_jsonb_field():
    import models
    assert hasattr(models, "Product"), "Product model not found"
    cols = [c.name for c in models.Product.__table__.columns]
    assert "attributes" in cols, "Product missing attributes column"
    assert "tags" in cols, "Product missing tags column"


def test_get_products_by_attribute_exists():
    from models import Product
    assert hasattr(Product, "get_products_by_attribute") or hasattr(
        __import__("models", fromlist=["get_products_by_attribute"]), "get_products_by_attribute"
    ), "get_products_by_attribute function not found"


def test_get_products_by_tag_exists():
    from models import Product
    assert hasattr(Product, "get_products_by_tag") or hasattr(
        __import__("models", fromlist=["get_products_by_tag"]), "get_products_by_tag"
    ), "get_products_by_tag function not found"


def test_get_product_attribute_exists():
    from models import Product
    assert hasattr(Product, "get_product_attribute") or hasattr(
        __import__("models", fromlist=["get_product_attribute"]), "get_product_attribute"
    ), "get_product_attribute function not found"


def test_product_creates_with_jsonb(session):
    from models import Product
    product = Product(name="Test Product", attributes={"color": "red", "size": "M"}, tags=["sale", "new"])
    session.add(product)
    session.commit()
    assert product.id is not None


def test_jsonb_defaults_to_empty(session):
    from models import Product
    product = Product(name="No Attr Product")
    session.add(product)
    session.commit()
    assert product.attributes is None or product.attributes == {}