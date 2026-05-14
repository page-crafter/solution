import { apiRequest } from './client'
import type { JobEvent, JobRead, TaskExecution } from '../types/api'

/** Loads a job status by id. */
export function fetchJob(jobId: string): Promise<JobRead> {
  return apiRequest<JobRead>(`/api/jobs/${jobId}`)
}

/** Loads chronological progress events for a job. */
export function fetchJobEvents(jobId: string): Promise<JobEvent[]> {
  return apiRequest<JobEvent[]>(`/api/jobs/${jobId}/events`)
}

/** Loads the recent persisted task execution history. */
export function fetchTaskHistory(limit = 50): Promise<TaskExecution[]> {
  return apiRequest<TaskExecution[]>(`/api/jobs/history?limit=${limit}`)
}

/** Cancels a job by id. */
export function cancelJob(jobId: string): Promise<JobRead> {
  return apiRequest<JobRead>(`/api/jobs/${jobId}/cancel`, { method: 'POST' })
}
