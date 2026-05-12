from sqlalchemy import text

from cm_shared.db.base import Base
from cm_shared.db.session import engine
from cm_shared.models import all as _models  # noqa: F401


def create_database_schema() -> None:
    """Create pgvector extension and ORM tables for local development."""
    with engine.begin() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    Base.metadata.create_all(bind=engine)
    with engine.begin() as connection:
        connection.execute(
            text(
                "ALTER TABLE confluence_pages "
                "ADD COLUMN IF NOT EXISTS space_name VARCHAR(255)"
            )
        )
        connection.execute(
            text(
                "ALTER TABLE confluence_pages "
                "ADD COLUMN IF NOT EXISTS parent_confluence_id VARCHAR(64)"
            )
        )
        connection.execute(
            text(
                "ALTER TABLE confluence_pages "
                "ADD COLUMN IF NOT EXISTS sort_order INTEGER NOT NULL DEFAULT 0"
            )
        )
        connection.execute(
            text(
                "ALTER TABLE confluence_pages "
                "ADD COLUMN IF NOT EXISTS is_placeholder BOOLEAN NOT NULL DEFAULT FALSE"
            )
        )
        connection.execute(
            text(
                "ALTER TABLE confluence_pages "
                "DROP COLUMN IF EXISTS has_confluence_draft"
            )
        )
        connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_confluence_pages_parent_confluence_id "
                "ON confluence_pages (parent_confluence_id)"
            )
        )
        connection.execute(
            text(
                """
                DO $$
                BEGIN
                    IF to_regclass('public.pipeline_runs') IS NOT NULL THEN
                        INSERT INTO page_edit_runs (
                            id,
                            page_id,
                            instruction,
                            status,
                            draft_status,
                            preview_status,
                            source_version,
                            task_id,
                            markdown_draft,
                            generated_storage_xhtml,
                            preview_html,
                            diff_text,
                            error_message,
                            created_at,
                            updated_at
                        )
                        SELECT
                            pipeline_runs.id,
                            pipeline_runs.page_id,
                            pipeline_runs.instruction,
                            pipeline_runs.status,
                            pipeline_runs.draft_status,
                            pipeline_runs.preview_status,
                            pipeline_runs.source_version,
                            pipeline_runs.task_id,
                            pipeline_runs.markdown_draft,
                            pipeline_runs.generated_storage_xhtml,
                            pipeline_runs.preview_html,
                            pipeline_runs.diff_text,
                            pipeline_runs.error_message,
                            pipeline_runs.created_at,
                            pipeline_runs.updated_at
                        FROM pipeline_runs
                        JOIN confluence_pages ON confluence_pages.id = pipeline_runs.page_id
                        ON CONFLICT (id) DO NOTHING;
                    END IF;

                    IF to_regclass('public.pipeline_edit_proposals') IS NOT NULL THEN
                        INSERT INTO page_proposals (
                            id,
                            page_id,
                            run_id,
                            instruction,
                            base_markdown,
                            base_source,
                            status,
                            task_id,
                            proposed_markdown,
                            diff_text,
                            summary,
                            error_message,
                            created_at,
                            updated_at
                        )
                        SELECT
                            pipeline_edit_proposals.id,
                            pipeline_edit_proposals.page_id,
                            page_edit_runs.id,
                            pipeline_edit_proposals.instruction,
                            pipeline_edit_proposals.base_markdown,
                            pipeline_edit_proposals.base_source,
                            pipeline_edit_proposals.status,
                            pipeline_edit_proposals.task_id,
                            pipeline_edit_proposals.proposed_markdown,
                            pipeline_edit_proposals.diff_text,
                            pipeline_edit_proposals.summary,
                            pipeline_edit_proposals.error_message,
                            pipeline_edit_proposals.created_at,
                            pipeline_edit_proposals.updated_at
                        FROM pipeline_edit_proposals
                        JOIN confluence_pages
                            ON confluence_pages.id = pipeline_edit_proposals.page_id
                        LEFT JOIN page_edit_runs
                            ON page_edit_runs.id = pipeline_edit_proposals.run_id
                        ON CONFLICT (id) DO NOTHING;
                    END IF;
                END $$;
                """
            )
        )
        connection.execute(
            text(
                """
                DELETE FROM draft_artifacts
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM page_edit_runs
                    WHERE page_edit_runs.id = draft_artifacts.run_id
                )
                """
            )
        )
        connection.execute(
            text(
                """
                UPDATE draft_versions
                SET proposal_id = NULL
                WHERE proposal_id IS NOT NULL
                AND NOT EXISTS (
                    SELECT 1
                    FROM page_proposals
                    WHERE page_proposals.id = draft_versions.proposal_id
                )
                """
            )
        )
        connection.execute(
            text(
                """
                DELETE FROM draft_versions
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM page_edit_runs
                    WHERE page_edit_runs.id = draft_versions.run_id
                )
                """
            )
        )
        connection.execute(
            text(
                "ALTER TABLE draft_artifacts "
                "DROP CONSTRAINT IF EXISTS draft_artifacts_run_id_fkey"
            )
        )
        connection.execute(
            text(
                "ALTER TABLE draft_artifacts "
                "ADD CONSTRAINT draft_artifacts_run_id_fkey "
                "FOREIGN KEY (run_id) REFERENCES page_edit_runs(id) ON DELETE CASCADE"
            )
        )
        connection.execute(
            text(
                "ALTER TABLE draft_versions "
                "DROP CONSTRAINT IF EXISTS draft_versions_run_id_fkey"
            )
        )
        connection.execute(
            text(
                "ALTER TABLE draft_versions "
                "ADD CONSTRAINT draft_versions_run_id_fkey "
                "FOREIGN KEY (run_id) REFERENCES page_edit_runs(id) ON DELETE CASCADE"
            )
        )
        connection.execute(
            text(
                "ALTER TABLE draft_versions "
                "DROP CONSTRAINT IF EXISTS draft_versions_proposal_id_fkey"
            )
        )
        connection.execute(
            text(
                "ALTER TABLE draft_versions "
                "ADD CONSTRAINT draft_versions_proposal_id_fkey "
                "FOREIGN KEY (proposal_id) REFERENCES page_proposals(id) ON DELETE SET NULL"
            )
        )
