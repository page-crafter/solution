import { apiRequest, jsonBody } from './client'
import type {
  ApplyProposalResponse,
  DraftVersion,
  PageProposal,
  PageEditRun,
} from '../types/api'

export interface CreateProposalOptions {
  baseProposalId?: string
  baseRunId?: string
  baseMarkdown?: string
}

/** Starts a documentation page editor for a page. */
export function createPageEditRun(pageId: number, instruction: string): Promise<PageEditRun> {
  return apiRequest<PageEditRun>(
    '/api/editor/runs',
    { method: 'POST', ...jsonBody({ page_id: pageId, instruction }) },
  )
}

/** Loads a page edit run with generated artifacts. */
export function fetchPageEditRun(runId: string): Promise<PageEditRun> {
  return apiRequest<PageEditRun>(`/api/editor/runs/${runId}`)
}

/** Loads validated Markdown draft versions for a run, newest first. */
export function fetchDraftVersions(runId: string): Promise<DraftVersion[]> {
  return apiRequest<DraftVersion[]>(`/api/editor/runs/${runId}/draft-versions`)
}

/** Loads the newest active draft run for a page when present. */
export function fetchActivePageEditRun(pageId: number): Promise<PageEditRun | null> {
  return apiRequest<PageEditRun | null>(`/api/editor/pages/${pageId}/active`)
}

/** Saves manual Markdown corrections. */
export function saveDraft(runId: string, markdownDraft: string): Promise<PageEditRun> {
  return apiRequest<PageEditRun>(
    `/api/editor/runs/${runId}/draft`,
    { method: 'PATCH', ...jsonBody({ markdown_draft: markdownDraft }) },
  )
}

/** Creates the first app-side draft from manually edited Markdown. */
export function createManualDraftRun(pageId: number, markdownDraft: string): Promise<PageEditRun> {
  return apiRequest<PageEditRun>(
    `/api/editor/pages/${pageId}/draft`,
    { method: 'POST', ...jsonBody({ markdown_draft: markdownDraft }) },
  )
}

/** Creates an LLM proposal without mutating the current draft. */
export function createProposal(
  pageId: number,
  message: string,
  options: CreateProposalOptions = {},
): Promise<PageProposal> {
  return apiRequest<PageProposal>(
    `/api/editor/pages/${pageId}/proposals`,
    {
      method: 'POST',
      ...jsonBody({
        message,
        base_proposal_id: options.baseProposalId,
        base_run_id: options.baseRunId,
        base_markdown: options.baseMarkdown,
      }),
    },
  )
}

/** Loads one Markdown proposal. */
export function fetchProposal(proposalId: string): Promise<PageProposal> {
  return apiRequest<PageProposal>(`/api/editor/proposals/${proposalId}`)
}

/** Applies a ready proposal to the draft and queues preview rendering. */
export function applyProposal(proposalId: string): Promise<ApplyProposalResponse> {
  return apiRequest<ApplyProposalResponse>(
    `/api/editor/proposals/${proposalId}/apply`,
    { method: 'POST' },
  )
}

/** Rejects a proposal without changing the draft. */
export function rejectProposal(proposalId: string): Promise<PageProposal> {
  return apiRequest<PageProposal>(
    `/api/editor/proposals/${proposalId}/reject`,
    { method: 'POST' },
  )
}

/** Restores a validated draft version and queues preview rendering. */
export function restoreDraftVersion(runId: string, versionId: number): Promise<PageEditRun> {
  return apiRequest<PageEditRun>(
    `/api/editor/runs/${runId}/draft-versions/${versionId}/restore`,
    { method: 'POST' },
  )
}


/** Queues final publication to Confluence. */
export function publishRun(runId: string): Promise<PageEditRun> {
  return apiRequest<PageEditRun>(`/api/editor/runs/${runId}/publish`, { method: 'POST' })
}

/** Cancels an app-side draft and clears generated artifacts. */
export function cancelRun(runId: string): Promise<PageEditRun> {
  return apiRequest<PageEditRun>(`/api/editor/runs/${runId}/cancel`, { method: 'POST' })
}

/** Cancels all active runs for a page and deletes all draft versions and artifacts. */
export function resetPageDraft(pageId: number): Promise<void> {
  return apiRequest<void>(`/api/editor/pages/${pageId}/reset`, { method: 'POST' })
}
