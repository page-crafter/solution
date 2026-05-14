import { apiRequest } from './client'
import type { SpaceStat } from '../types/api'

/** Loads per-space page, indexing, draft, and sync summary metrics. */
export function fetchSpaces(): Promise<SpaceStat[]> {
  return apiRequest<SpaceStat[]>('/api/spaces')
}
