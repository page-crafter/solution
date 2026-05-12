import { apiRequest } from './client'
import type { LightRagStatus } from '../types/api'

export function fetchLightRagStatus(): Promise<LightRagStatus> {
  return apiRequest<LightRagStatus>('/api/lightrag/status')
}
