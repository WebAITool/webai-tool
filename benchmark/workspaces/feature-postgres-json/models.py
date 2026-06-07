from sqlalchemy import Column, Integer, String, DateTime, func
from sqlalchemy.orm import declarative_base
from sqlalchemy.dialects.postgresql import JSONB

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    attributes = Column(JSONB, default={})
    tags = Column(JSONB, default=[])
    created_at = Column(DateTime, server_default=func.now())

    @classmethod
    def get_products_by_attribute(cls, session, key, value):
        return session.query(cls).filter(cls.attributes.contains({key: value})).all()

    @classmethod
    def get_products_by_tag(cls, session, tag):
        return session.query(cls).filter(cls.tags.has_key(tag)).all()

    @classmethod
    def get_product_attribute(cls, session, product_id, key):
        product = session.query(cls).filter(cls.id == product_id).first()
        if product is None:
            return None
        if not hasattr(product, 'attributes') or product.attributes is None:
            return None
        return product.attributes.get(key)
