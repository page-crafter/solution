import { apiRequest } from './client'
import type { KpiCard } from '../types/api'

/** Loads dashboard KPI cards from the API. */
export function fetchKpis(): Promise<KpiCard[]> {
  return apiRequest<KpiCard[]>('/api/kpis')
}

