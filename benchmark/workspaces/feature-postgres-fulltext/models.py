from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    func,
    event,
)
from sqlalchemy.orm import declarative_base
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.schema import Index

Base = declarative_base()


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    category = Column(String(50), default="general")
    created_at = Column(DateTime, server_default=func.now())
    search_vector = Column(TSVECTOR)

    __table_args__ = (
        Index("ix_document_search_vector", "search_vector", postgresql_using="gin"),
    )


@event.listens_for(Document, "before_insert")
@event.listens_for(Document, "before_update")
def update_search_vector(mapper, connection, target):
    target.search_vector = (
        func.setweight(
            func.to_tsvector("english", func.coalesce(target.title, "")), "A"
        )
        + func.setweight(
            func.to_tsvector("english", func.coalesce(target.content, "")), "B"
        )
    )


def search_documents(session, query_text):
    from sqlalchemy import text

    query = func.plainto_tsquery("english", query_text)
    stmt = (
        session.query(
            Document,
            func.ts_rank(Document.search_vector, query).label("relevance"),
        )
        .filter(Document.search_vector.op("@@")(query))
        .order_by(text("relevance DESC"))
    )
    return stmt.all()
