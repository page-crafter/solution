import { apiRequest } from './client'
import type { SpaceStat } from '../types/api'

export function fetchSpaces(): Promise<SpaceStat[]> {
  return apiRequest<SpaceStat[]>('/api/spaces')
}
