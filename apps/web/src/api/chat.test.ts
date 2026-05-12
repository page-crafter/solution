import { afterEach, describe, expect, it, vi } from 'vitest'
import { setAuthTokenProvider } from './client'
import { streamChatQuestion } from './chat'
import type { ChatQuerySettings } from '../types/api'

const settings: ChatQuerySettings = {
  mode: 'mix',
  user_prompt: '',
  top_k: 40,
  chunk_top_k: 20,
  max_entity_tokens: 6000,
  max_relation_tokens: 8000,
  max_total_tokens: 30000,
  enable_rerank: true,
  only_need_context: false,
  only_need_prompt: false,
}

function ndjsonResponse(lines: string[]): Response {
  const encoder = new TextEncoder()
  return new Response(
    new ReadableStream({
      start(controller) {
        for (const line of lines) {
          controller.enqueue(encoder.encode(`${line}\n`))
        }
        controller.close()
      },
    }),
    {
      status: 200,
      headers: { 'Content-Type': 'application/x-ndjson' },
    },
  )
}

describe('streamChatQuestion', () => {
  afterEach(() => {
    setAuthTokenProvider(() => undefined)
    vi.unstubAllGlobals()
  })

  it('dispatches stats events from the NDJSON stream', async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(
      ndjsonResponse([
        JSON.stringify({
          stats: {
            phase: 'started',
            elapsedMs: 0,
            historyMessageCount: 2,
            historyChars: 24,
            responseChars: 0,
            chunkCount: 0,
            referenceCount: 0,
            streamEventCount: 0,
            tokenUsage: null,
          },
        }),
      ]),
    )
    vi.stubGlobal('fetch', fetchMock)
    const onStats = vi.fn()

    await streamChatQuestion('session-1', 'Hello', settings, { onStats })

    expect(onStats).toHaveBeenCalledWith({
      phase: 'started',
      elapsedMs: 0,
      historyMessageCount: 2,
      historyChars: 24,
      responseChars: 0,
      chunkCount: 0,
      referenceCount: 0,
      streamEventCount: 0,
      tokenUsage: null,
    })
  })
})
