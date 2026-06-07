"""Database module with SQLAlchemy engine, session, and get_db() dependency."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

Base = declarative_base()

engine = create_engine("sqlite:///app.db")
SessionLocal = sessionmaker(bind=engine)


def get_db():
    """Yield a database session and ensure it is closed after use."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Create all tables on import (when this module is first loaded)
Base.metadata.create_all(bind=engine)
