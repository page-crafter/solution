import { apiRequest, jsonBody } from './client'
import type { ConfluencePage, JobRead, PageDetail } from '../types/api'

export type PageMovePosition = 'append' | 'before' | 'after'

export interface CreateEmptyPagePayload {
  title: string
  parent_id?: string | null
}

/** Loads all synced Confluence pages. */
export function fetchPages(): Promise<ConfluencePage[]> {
  return apiRequest<ConfluencePage[]>('/api/confluence/pages')
}

/** Loads one page with source XHTML and extracted text. */
export function fetchPage(pageId: number): Promise<PageDetail> {
  return apiRequest<PageDetail>(`/api/confluence/pages/${pageId}`)
}

/** Queues a single-page refresh job. */
export function refreshPage(pageId: number): Promise<JobRead> {
  return apiRequest<JobRead>(`/api/confluence/pages/${pageId}/refresh`, { method: 'POST' })
}

/** Queues creation of an empty Confluence page for later processing. */
export function createEmptyPage(payload: CreateEmptyPagePayload): Promise<JobRead> {
  return apiRequest<JobRead>(
    '/api/confluence/pages',
    { method: 'POST', ...jsonBody(payload) },
  )
}

/** Queues a page move job. */
export function movePage(
  pageId: number,
  targetId: string,
  position: PageMovePosition = 'append',
): Promise<JobRead> {
  return apiRequest<JobRead>(
    `/api/confluence/pages/${pageId}/move`,
    { method: 'POST', ...jsonBody({ target_id: targetId, position }) },
  )
}

/** Queues a page deletion job. */
export function deletePage(pageId: number): Promise<JobRead> {
  return apiRequest<JobRead>(`/api/confluence/pages/${pageId}`, { method: 'DELETE' })
}

/** Queues a full-space synchronization job. */
export function syncSpace(): Promise<JobRead> {
  return apiRequest<JobRead>('/api/sync/runs', { method: 'POST' })
}
