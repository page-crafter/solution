export type DraftState =
  | 'Published'
  | 'Draft in progress'
  | 'Draft generated'
  | 'Preview ready'
  | 'Publish blocked'

export interface KpiCard {
  label: string
  value: string
  trend: string
  tone: string
}

export interface JobRead {
  id: string
  status: string
  task_id?: string | null
  message?: string | null
}

export interface JobEvent {
  id: number
  job_id: string
  level: string
  message: string
  created_at: string
}

export interface TaskExecution {
  id: number
  job_id: string
  task_id?: string | null
  task_name: string
  actor: string
  status: string
  message?: string | null
  created_at: string
  started_at?: string | null
  finished_at?: string | null
  updated_at: string
}

export interface ConfluencePage {
  id: number
  confluence_id: string
  space_key: string
  space_name?: string | null
  parent_confluence_id?: string | null
  sort_order: number
  title: string
  status: string
  version_number: number
  web_url?: string | null
  edit_url?: string | null
  tiny_url?: string | null
  is_placeholder: boolean
  draft_state: DraftState
  last_synced_at: string
}

export interface PageDetail extends ConfluencePage {
  source_storage_xhtml: string
  extracted_text: string
}

export interface PageEditRun {
  id: string
  page_id: number
  instruction: string
  status: string
  draft_status: DraftState
  preview_status: string
  source_version: number
  markdown_draft?: string | null
  generated_storage_xhtml?: string | null
  preview_html?: string | null
  diff_text?: string | null
  error_message?: string | null
  created_at: string
  updated_at: string
}

export type PageProposalStatus =
  | 'queued'
  | 'generating'
  | 'ready'
  | 'applied'
  | 'rejected'
  | 'failed'

export interface PageProposal {
  id: string
  page_id: number
  run_id?: string | null
  instruction: string
  base_markdown: string
  base_source: 'page' | 'draft' | string
  status: PageProposalStatus
  proposed_markdown?: string | null
  diff_text?: string | null
  summary?: string | null
  error_message?: string | null
  created_at: string
  updated_at: string
}

export interface DraftVersion {
  id: number
  run_id: string
  version_number: number
  markdown_draft: string
  change_source: string
  actor: string
  proposal_id?: string | null
  restored_from_version_id?: number | null
  created_at: string
}

export interface ApplyProposalResponse {
  proposal: PageProposal
  run: PageEditRun
}

export interface ChatSession {
  id: string
  title: string
}

export interface ChatMessage {
  id: number
  session_id: string
  role: 'user' | 'assistant'
  content: string
  citations_json: string
}

export type ChatQueryMode = 'naive' | 'local' | 'global' | 'hybrid' | 'mix' | 'bypass'

export interface ChatQuerySettings {
  mode: ChatQueryMode
  user_prompt?: string
  top_k: number
  chunk_top_k: number
  max_entity_tokens: number
  max_relation_tokens: number
  max_total_tokens: number
  enable_rerank: boolean
  only_need_context: boolean
  only_need_prompt: boolean
}

export interface ChatStreamReferencesEvent {
  references: Record<string, unknown>[]
}

export interface ChatStreamDeltaEvent {
  delta: string
}

export type ChatStreamStatsPhase = 'started' | 'streaming' | 'completed' | 'failed'

export interface ChatStreamTokenUsage {
  promptTokens?: number
  completionTokens?: number
  totalTokens?: number
}

export interface ChatStreamStats {
  phase: ChatStreamStatsPhase
  elapsedMs: number
  historyMessageCount: number
  historyChars: number
  responseChars: number
  chunkCount: number
  referenceCount: number
  streamEventCount: number
  tokenUsage?: ChatStreamTokenUsage | null
  error?: string
}

export interface ChatStreamStatsEvent {
  stats: ChatStreamStats
}

export interface ChatStreamAssistantEvent {
  assistant_message: ChatMessage
}

export interface ChatStreamErrorEvent {
  error: string
}

export type ChatStreamEvent =
  | ChatStreamReferencesEvent
  | ChatStreamDeltaEvent
  | ChatStreamStatsEvent
  | ChatStreamAssistantEvent
  | ChatStreamErrorEvent

export interface SpaceStat {
  space_key: string
  space_name: string
  page_count: number
  indexed_count: number
  coverage_pct: number
  open_drafts: number
  last_synced_at: string
}

export interface LightRagDocCounts {
  pending: number
  processing: number
  preprocessed: number
  processed: number
  failed: number
  all: number
}

export interface LightRagPipelineStatus {
  busy: boolean
  job_name: string
  docs: number
  batchs: number
  cur_batch: number
  latest_message: string
}

export interface LightRagStatus {
  healthy: boolean
  core_version: string
  llm_model: string
  embedding_model: string
  pipeline: LightRagPipelineStatus
  doc_counts: LightRagDocCounts
}
