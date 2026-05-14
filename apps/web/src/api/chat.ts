import { apiRawRequest, apiRequest, jsonBody } from './client'
import type {
  ChatMessage,
  ChatSession,
  ChatStreamEvent,
  ChatStreamStats,
  ChatQuerySettings,
} from '../types/api'

/** Creates a documentation chat session. */
export function createChatSession(title = 'Documentation chat'): Promise<ChatSession> {
  return apiRequest<ChatSession>('/api/chat/sessions', { method: 'POST', ...jsonBody({ title }) })
}

/** Loads messages for a chat session. */
export function fetchChatMessages(sessionId: string): Promise<ChatMessage[]> {
  return apiRequest<ChatMessage[]>(`/api/chat/sessions/${sessionId}/messages`)
}


export interface ChatStreamHandlers {
  onDelta?: (delta: string) => void
  onReferences?: (references: Record<string, unknown>[]) => void
  onStats?: (stats: ChatStreamStats) => void
  onAssistantMessage?: (message: ChatMessage) => void
  onError?: (error: string) => void
}

/** Dispatches one parsed NDJSON stream event to the matching optional handler. */
function handleStreamEvent(event: ChatStreamEvent, handlers: ChatStreamHandlers): void {
  if ('delta' in event) {
    handlers.onDelta?.(event.delta)
  }
  if ('references' in event) {
    handlers.onReferences?.(event.references)
  }
  if ('stats' in event) {
    handlers.onStats?.(event.stats)
  }
  if ('assistant_message' in event) {
    handlers.onAssistantMessage?.(event.assistant_message)
  }
  if ('error' in event) {
    handlers.onError?.(event.error)
  }
}

/** Streams a chat answer through the FastAPI backend. */
export async function streamChatQuestion(
  sessionId: string,
  message: string,
  settings: ChatQuerySettings,
  handlers: ChatStreamHandlers,
): Promise<void> {
  const response = await apiRawRequest(
    `/api/chat/sessions/${sessionId}/stream`,
    {
      method: 'POST',
      headers: { Accept: 'application/x-ndjson' },
      ...jsonBody({ message, settings }),
    },
  )

  if (!response.ok) {
    const errorText = await response.text()
    throw new Error(errorText || `Request failed with ${response.status}`)
  }
  if (!response.body) {
    throw new Error('Streaming response body is empty')
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() ?? ''
    for (const line of lines) {
      if (!line.trim()) continue
      handleStreamEvent(JSON.parse(line) as ChatStreamEvent, handlers)
    }
  }

  if (buffer.trim()) {
    handleStreamEvent(JSON.parse(buffer) as ChatStreamEvent, handlers)
  }
}
