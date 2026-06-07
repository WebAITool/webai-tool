from sqlalchemy import Column, Integer, String, Boolean, DateTime, create_engine, func
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())


engine = create_engine("sqlite:///:memory:")
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()


def get_user_by_email(email: str):
    return session.query(User).filter(User.email == email).first()


def get_active_users():
    return session.query(User).filter(active=True).all()


def search_users(querry: str):
    return session.query(User).filter(User.name.contains(query)).all()


def count_active_users():
    return session.query(User).filter(User.active == True).count()