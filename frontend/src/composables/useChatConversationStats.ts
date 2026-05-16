import { computed, onUnmounted, shallowRef, type ComputedRef, type Ref } from 'vue'
import type { ChatMessage, ChatStreamStats, ChatStreamTokenUsage } from '../types/api'

export type ChatStatsStatus = 'idle' | 'streaming' | 'completed' | 'failed'

export interface ChatLiveRequestStats {
  status: ChatStatsStatus
  elapsedMs: number
  responseChars: number
  responseWords: number
  chunkCount: number
  referenceCount: number
  historyMessageCount: number
  historyChars: number
  streamEventCount: number
  serverElapsedMs?: number
  tokenUsage?: ChatStreamTokenUsage | null
  error?: string
}

export interface ChatConversationTotals {
  requestCount: number
  assistantChars: number
  assistantWords: number
  historyMessageCount: number
  historyChars: number
  responseChars: number
  chunkCount: number
  referenceCount: number
  streamEventCount: number
  clientElapsedMs: number
  serverElapsedMs: number
  tokenUsage?: ChatStreamTokenUsage | null
}

export interface ChatConversationStats {
  status: ChatStatsStatus
  questionCount: number
  answerCount: number
  messageCount: number
  totalChars: number
  totalWords: number
  referenceCount: number
  errorCount: number
  measuredElapsedMs: number
  totals: ChatConversationTotals
  current: ChatLiveRequestStats
}

interface UseChatConversationStatsOptions {
  messages: Readonly<Ref<ChatMessage[]>>
  streamingContent: Readonly<Ref<string>>
}

interface LiveRequestState extends Omit<ChatLiveRequestStats, 'elapsedMs' | 'responseWords'> {
  startedAt?: number
  finishedAt?: number
  elapsedMs: number
  countedInTotals?: boolean
}

interface StreamTotalsState {
  requestCount: number
  historyMessageCount: number
  historyChars: number
  responseChars: number
  chunkCount: number
  referenceCount: number
  streamEventCount: number
  clientElapsedMs: number
  serverElapsedMs: number
  tokenUsage: ChatStreamTokenUsage | null
}

/** Creates the neutral live-request stats state used before streaming starts. */
function createIdleLiveRequest(): LiveRequestState {
  return {
    status: 'idle',
    elapsedMs: 0,
    responseChars: 0,
    chunkCount: 0,
    referenceCount: 0,
    historyMessageCount: 0,
    historyChars: 0,
    streamEventCount: 0,
    tokenUsage: null,
  }
}

/** Counts whitespace-delimited words in text content. */
function wordCount(value: string): number {
  const trimmed = value.trim()
  return trimmed ? trimmed.split(/\s+/).length : 0
}

/** Counts parsed citation entries on a persisted chat message. */
function citationCount(message: ChatMessage): number {
  try {
    const parsed = JSON.parse(message.citations_json)
    return Array.isArray(parsed) ? parsed.length : 0
  } catch {
    return 0
  }
}

/** Creates the neutral aggregate stream totals state. */
function createStreamTotals(): StreamTotalsState {
  return {
    requestCount: 0,
    historyMessageCount: 0,
    historyChars: 0,
    responseChars: 0,
    chunkCount: 0,
    referenceCount: 0,
    streamEventCount: 0,
    clientElapsedMs: 0,
    serverElapsedMs: 0,
    tokenUsage: null,
  }
}

/** Adds one request's token usage into cumulative token usage totals. */
function addTokenUsage(
  totalUsage: ChatStreamTokenUsage | null,
  requestUsage: ChatStreamTokenUsage | null | undefined,
): ChatStreamTokenUsage | null {
  if (!requestUsage) return totalUsage

  const nextUsage: ChatStreamTokenUsage = { ...(totalUsage ?? {}) }
  if (typeof requestUsage.promptTokens === 'number') {
    nextUsage.promptTokens = (nextUsage.promptTokens ?? 0) + requestUsage.promptTokens
  }
  if (typeof requestUsage.completionTokens === 'number') {
    nextUsage.completionTokens = (nextUsage.completionTokens ?? 0) + requestUsage.completionTokens
  }
  if (typeof requestUsage.totalTokens === 'number') {
    nextUsage.totalTokens = (nextUsage.totalTokens ?? 0) + requestUsage.totalTokens
  }
  return Object.keys(nextUsage).length > 0 ? nextUsage : null
}

/** Tracks live and cumulative chat conversation metrics for streamed answers. */
export function useChatConversationStats(
  options: UseChatConversationStatsOptions,
): {
  conversationStats: ComputedRef<ChatConversationStats>
  beginRequest: () => void
  recordDelta: (delta: string) => void
  recordReferences: (references: Record<string, unknown>[]) => void
  recordServerStats: (stats: ChatStreamStats) => void
  recordStreamError: (error: string) => void
  completeRequest: () => void
  resetStats: () => void
} {
  const liveRequest = shallowRef<LiveRequestState>(createIdleLiveRequest())
  const streamTotals = shallowRef<StreamTotalsState>(createStreamTotals())
  const errorCount = shallowRef(0)
  const clockTick = shallowRef(Date.now())
  let timerId: number | undefined

  /** Computes elapsed time for the active or last finished live request. */
  function activeElapsedMs(): number {
    const live = liveRequest.value
    if (!live.startedAt) return live.elapsedMs
    return Math.max(0, (live.finishedAt ?? clockTick.value) - live.startedAt)
  }

  /** Starts the short interval clock used while a request is streaming. */
  function startClock(): void {
    stopClock()
    clockTick.value = Date.now()
    timerId = window.setInterval(() => {
      clockTick.value = Date.now()
    }, 250)
  }

  /** Stops the live request interval clock. */
  function stopClock(): void {
    if (timerId === undefined) return
    window.clearInterval(timerId)
    timerId = undefined
  }

  /** Patches live request state while preserving Vue change detection. */
  function patchLiveRequest(patch: Partial<LiveRequestState>): void {
    liveRequest.value = { ...liveRequest.value, ...patch }
  }

  /** Adds a completed live request into cumulative stream totals once. */
  function addLiveRequestToTotals(live: LiveRequestState, elapsedMs: number): void {
    if (live.countedInTotals) return
    streamTotals.value = {
      requestCount: streamTotals.value.requestCount + 1,
      historyMessageCount: streamTotals.value.historyMessageCount + live.historyMessageCount,
      historyChars: streamTotals.value.historyChars + live.historyChars,
      responseChars: streamTotals.value.responseChars + live.responseChars,
      chunkCount: streamTotals.value.chunkCount + live.chunkCount,
      referenceCount: streamTotals.value.referenceCount + live.referenceCount,
      streamEventCount: streamTotals.value.streamEventCount + live.streamEventCount,
      clientElapsedMs: streamTotals.value.clientElapsedMs + elapsedMs,
      serverElapsedMs: streamTotals.value.serverElapsedMs + (live.serverElapsedMs ?? 0),
      tokenUsage: addTokenUsage(streamTotals.value.tokenUsage, live.tokenUsage),
    }
  }

  /** Marks the live request completed or failed, records totals, and stops the clock. */
  function finishRequest(status: Exclude<ChatStatsStatus, 'idle' | 'streaming'>, error?: string): void {
    const live = liveRequest.value
    if (live.status === status || (live.status === 'failed' && status === 'completed')) return

    const finishedAt = live.finishedAt ?? Date.now()
    const elapsedMs = Math.max(0, finishedAt - (live.startedAt ?? finishedAt))
    addLiveRequestToTotals(live, elapsedMs)
    liveRequest.value = {
      ...live,
      status,
      countedInTotals: true,
      finishedAt,
      elapsedMs,
      error: error ?? live.error,
    }
    stopClock()
  }

  /** Starts tracking metrics for a newly submitted chat request. */
  function beginRequest(): void {
    liveRequest.value = {
      ...createIdleLiveRequest(),
      status: 'streaming',
      startedAt: Date.now(),
    }
    startClock()
  }

  /** Records one streamed text delta and increments chunk counts. */
  function recordDelta(delta: string): void {
    const live = liveRequest.value
    patchLiveRequest({
      responseChars: live.responseChars + delta.length,
      chunkCount: live.chunkCount + 1,
    })
  }

  /** Records the latest reference count reported by the streaming backend. */
  function recordReferences(references: Record<string, unknown>[]): void {
    patchLiveRequest({ referenceCount: references.length })
  }

  /** Records backend-reported stream metrics and reacts to terminal phases. */
  function recordServerStats(stats: ChatStreamStats): void {
    patchLiveRequest({
      historyMessageCount: stats.historyMessageCount,
      historyChars: stats.historyChars,
      responseChars: stats.responseChars,
      chunkCount: stats.chunkCount,
      referenceCount: stats.referenceCount,
      streamEventCount: stats.streamEventCount,
      serverElapsedMs: stats.elapsedMs,
      tokenUsage: stats.tokenUsage ?? null,
      error: stats.error ?? liveRequest.value.error,
    })

    if (stats.phase === 'failed') {
      recordStreamError(stats.error ?? 'Stream failed')
    }
    if (stats.phase === 'completed') {
      completeRequest()
    }
  }

  /** Marks the live request failed and increments the conversation error count once. */
  function recordStreamError(error: string): void {
    if (liveRequest.value.status !== 'failed') {
      errorCount.value += 1
    }
    finishRequest('failed', error)
  }

  /** Marks the live request successfully completed. */
  function completeRequest(): void {
    finishRequest('completed')
  }

  /** Clears live and cumulative metrics, including the active clock. */
  function resetStats(): void {
    stopClock()
    liveRequest.value = createIdleLiveRequest()
    streamTotals.value = createStreamTotals()
    errorCount.value = 0
  }

  const currentRequest = computed<ChatLiveRequestStats>(() => {
    const live = liveRequest.value
    const responseContent = options.streamingContent.value
    const responseChars = Math.max(live.responseChars, responseContent.length)
    return {
      status: live.status,
      elapsedMs: activeElapsedMs(),
      responseChars,
      responseWords: wordCount(responseContent),
      chunkCount: live.chunkCount,
      referenceCount: live.referenceCount,
      historyMessageCount: live.historyMessageCount,
      historyChars: live.historyChars,
      streamEventCount: live.streamEventCount,
      serverElapsedMs: live.serverElapsedMs,
      tokenUsage: live.tokenUsage,
      error: live.error,
    }
  })

  const conversationStats = computed<ChatConversationStats>(() => {
    const persistedMessages = options.messages.value
    const streamingAnswerChars = options.streamingContent.value.length
    const includeLiveAnswer = streamingAnswerChars > 0
    const persistedChars = persistedMessages.reduce(
      (total, message) => total + message.content.length,
      0,
    )
    const persistedWords = persistedMessages.reduce(
      (total, message) => total + wordCount(message.content),
      0,
    )
    const persistedReferenceCount = persistedMessages.reduce(
      (total, message) => total + citationCount(message),
      0,
    )
    const persistedAssistantContent = persistedMessages
      .filter((message) => message.role === 'assistant')
      .map((message) => message.content)
      .join('\n')
    const liveReferencesArePersisted =
      liveRequest.value.status === 'completed' && !includeLiveAnswer
    const activeElapsedMs =
      liveRequest.value.status === 'streaming' ? currentRequest.value.elapsedMs : 0
    const activeLiveRequest = liveRequest.value.countedInTotals ? createIdleLiveRequest() : liveRequest.value
    const activeServerElapsedMs = activeLiveRequest.serverElapsedMs ?? 0
    const activeTokenUsage = addTokenUsage(streamTotals.value.tokenUsage, activeLiveRequest.tokenUsage)
    const assistantChars = persistedAssistantContent.length + streamingAnswerChars
    const assistantWords =
      wordCount(persistedAssistantContent) + wordCount(options.streamingContent.value)

    return {
      status: currentRequest.value.status,
      questionCount: persistedMessages.filter((message) => message.role === 'user').length,
      answerCount:
        persistedMessages.filter((message) => message.role === 'assistant').length
        + (includeLiveAnswer ? 1 : 0),
      messageCount: persistedMessages.length + (includeLiveAnswer ? 1 : 0),
      totalChars: persistedChars + streamingAnswerChars,
      totalWords: persistedWords + wordCount(options.streamingContent.value),
      referenceCount:
        persistedReferenceCount
        + (liveReferencesArePersisted ? 0 : currentRequest.value.referenceCount),
      errorCount: errorCount.value,
      measuredElapsedMs: streamTotals.value.clientElapsedMs + activeElapsedMs,
      totals: {
        requestCount:
          streamTotals.value.requestCount
          + (activeLiveRequest.startedAt ? 1 : 0),
        assistantChars,
        assistantWords,
        historyMessageCount:
          streamTotals.value.historyMessageCount + activeLiveRequest.historyMessageCount,
        historyChars: streamTotals.value.historyChars + activeLiveRequest.historyChars,
        responseChars: streamTotals.value.responseChars + activeLiveRequest.responseChars,
        chunkCount: streamTotals.value.chunkCount + activeLiveRequest.chunkCount,
        referenceCount:
          streamTotals.value.referenceCount
          + (liveReferencesArePersisted ? 0 : activeLiveRequest.referenceCount),
        streamEventCount:
          streamTotals.value.streamEventCount + activeLiveRequest.streamEventCount,
        clientElapsedMs: streamTotals.value.clientElapsedMs + activeElapsedMs,
        serverElapsedMs: streamTotals.value.serverElapsedMs + activeServerElapsedMs,
        tokenUsage: activeTokenUsage,
      },
      current: currentRequest.value,
    }
  })

  onUnmounted(stopClock)

  return {
    conversationStats,
    beginRequest,
    recordDelta,
    recordReferences,
    recordServerStats,
    recordStreamError,
    completeRequest,
    resetStats,
  }
}
