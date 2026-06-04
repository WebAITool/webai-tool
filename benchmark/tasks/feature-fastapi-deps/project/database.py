"""Database module — needs get_db() implementation."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

Base = declarative_base()

# TODO: implement engine, SessionLocal, and get_db()
engine = None
SessionLocal = None


def get_db():
    """Yield a database session. TODO: implement."""
    pass
