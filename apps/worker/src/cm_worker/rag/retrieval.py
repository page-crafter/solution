from sqlalchemy import select
from sqlalchemy.orm import Session

from cm_shared.models.confluence import DocumentChunk
from cm_worker.rag.embedding import embed_text


def retrieve_context(
    session: Session,
    question: str,
    limit: int = 6,
    page_id: int | None = None,
) -> list[DocumentChunk]:
    """Retrieve relevant documentation chunks from pgvector."""
    query_embedding = embed_text(question)
    statement = select(DocumentChunk)
    if page_id is not None:
        statement = statement.where(DocumentChunk.page_id == page_id)
    statement = statement.order_by(
        DocumentChunk.embedding.l2_distance(query_embedding)
    ).limit(limit)
    return list(session.scalars(statement).all())
