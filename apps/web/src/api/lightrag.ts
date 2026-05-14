import { apiRequest } from './client'
import type { LightRagStatus } from '../types/api'

/** Loads health, model, pipeline, and document counts for the LightRAG service. */
export function fetchLightRagStatus(): Promise<LightRagStatus> {
  return apiRequest<LightRagStatus>('/api/lightrag/status')
}
