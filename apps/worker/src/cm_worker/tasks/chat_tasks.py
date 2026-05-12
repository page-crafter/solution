import json

from cm_shared.db.session import SessionLocal
from cm_shared.models.chat import ChatMessage
from cm_worker.celery_app import celery_app
from cm_worker.page_editor.generate_markdown import create_chat_model
from cm_worker.rag.retrieval import retrieve_context
from cm_worker.tasks.history import current_task_id, mark_task_finished, mark_task_running


def build_answer_prompt(question: str, context: str) -> str:
    """Build a grounded documentation chat prompt."""
    return (
        "Answer using only the documentation context. If the answer is not present, say so.\n\n"
        f"Question:\n{question}\n\nDocumentation context:\n{context}"
    )


@celery_app.task(name="cm_worker.answer_question")
def answer_question(session_id: str, message_id: int) -> None:
    """Answer a chat question using pgvector-backed Confluence context."""
    task_name = "cm_worker.answer_question"
    job_id = current_task_id() or f"{session_id}:{message_id}"
    with SessionLocal() as session:
        message = session.get(ChatMessage, message_id)
        if message is None:
            mark_task_finished(
                session,
                job_id=job_id,
                task_name=task_name,
                status="failed",
                message="Chat message not found",
            )
            session.commit()
            return
        mark_task_running(
            session,
            job_id=job_id,
            task_name=task_name,
            message="Generating chat answer",
        )
        session.commit()
        try:
            chunks = retrieve_context(session, message.content)
            context = "\n\n".join(chunk.content for chunk in chunks)
            citations = [
                {
                    "pageId": chunk.page_id,
                    "confluenceId": chunk.confluence_id,
                    "snippet": chunk.content[:220],
                }
                for chunk in chunks
            ]
            model = create_chat_model()
            if model is None:
                answer = f"I found {len(chunks)} relevant documentation sections. {context[:1200]}"
            else:
                response = model.invoke(build_answer_prompt(message.content, context))
                answer = str(response.content)
            session.add(
                ChatMessage(
                    session_id=session_id,
                    role="assistant",
                    content=answer,
                    citations_json=json.dumps(citations),
                )
            )
            mark_task_finished(
                session,
                job_id=job_id,
                task_name=task_name,
                status="completed",
                message="Chat answer generated",
            )
        except Exception as exc:  # noqa: BLE001
            mark_task_finished(
                session,
                job_id=job_id,
                task_name=task_name,
                status="failed",
                message=str(exc),
            )
            session.commit()
            raise
        session.commit()
