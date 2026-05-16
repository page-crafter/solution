<script setup lang="ts">
import { computed, onMounted, shallowRef } from 'vue'
import { useRoute } from 'vue-router'
import { createChatSession, fetchChatMessages, streamChatQuestion } from '../api/chat'
import { defaultChatSettings } from '../composables/useChatSettings'
import { getRuntimeConfig } from '../config/runtime'
import { useAuthStore } from '../stores/auth'
import type { ChatMessage, ChatQuerySettings, ChatSession } from '../types/api'
import AppSpinner from '../components/common/AppSpinner.vue'
import ChatComposer from '../components/chat/ChatComposer.vue'
import ChatMessages from '../components/chat/ChatMessages.vue'

const auth = useAuthStore()
const route = useRoute()
const publicAccess = computed(() => getRuntimeConfig().chat.publicAccess)

const session = shallowRef<ChatSession>()
const messages = shallowRef<ChatMessage[]>([])
const draftMessage = shallowRef('')
const streamingContent = shallowRef('')
const streamingError = shallowRef('')
const streaming = shallowRef(false)
const chatGeneration = shallowRef(0)

/** Reads embed query parameters into chat settings for this embedded session. */
function readQuerySettings(): ChatQuerySettings {
  const q = route.query
  const s = { ...defaultChatSettings }
  if (typeof q.mode === 'string') s.mode = q.mode as ChatQuerySettings['mode']
  if (typeof q.user_prompt === 'string') s.user_prompt = q.user_prompt
  if (q.top_k) s.top_k = Math.max(1, Number(q.top_k) || s.top_k)
  if (q.chunk_top_k) s.chunk_top_k = Math.max(1, Number(q.chunk_top_k) || s.chunk_top_k)
  if (q.max_entity_tokens) s.max_entity_tokens = Math.max(1, Number(q.max_entity_tokens) || s.max_entity_tokens)
  if (q.max_relation_tokens) s.max_relation_tokens = Math.max(1, Number(q.max_relation_tokens) || s.max_relation_tokens)
  if (q.max_total_tokens) s.max_total_tokens = Math.max(1, Number(q.max_total_tokens) || s.max_total_tokens)
  if (q.enable_rerank === 'false') s.enable_rerank = false
  if (q.only_need_context === 'true') s.only_need_context = true
  if (q.only_need_prompt === 'true') s.only_need_prompt = true
  return s
}

/** Returns whether the embed chat has visible conversation or error content. */
const hasChatContent = () =>
  messages.value.length > 0 || streamingContent.value.length > 0 || streamingError.value.length > 0

/** Creates the embedded chat session and loads any persisted messages. */
async function initChat(): Promise<void> {
  session.value = await createChatSession()
  messages.value = await fetchChatMessages(session.value.id)
}

/** Clears embed state and starts a fresh chat session. */
async function clearChat(): Promise<void> {
  chatGeneration.value += 1
  messages.value = []
  streamingContent.value = ''
  streamingError.value = ''
  streaming.value = false
  session.value = await createChatSession()
}

/** Streams one embedded chat answer while ignoring stale responses after resets. */
async function askQuestion(): Promise<void> {
  if (!session.value || streaming.value) return
  const message = draftMessage.value.trim()
  if (!message) return

  const sessionId = session.value.id
  const requestGeneration = chatGeneration.value
  messages.value = [
    ...messages.value,
    { id: -Date.now(), session_id: sessionId, role: 'user', content: message, citations_json: '[]' },
  ]
  draftMessage.value = ''
  streaming.value = true
  streamingContent.value = ''
  streamingError.value = ''

  /** Returns whether streamed callbacks still belong to the active embedded session. */
  const isCurrent = () => chatGeneration.value === requestGeneration && session.value?.id === sessionId
  let assistantMessage: ChatMessage | undefined
  let loadedPersisted = false

  try {
    await streamChatQuestion(sessionId, message, readQuerySettings(), {
      onDelta: (delta) => { if (isCurrent()) streamingContent.value += delta },
      onReferences: () => {},
      onStats: () => {},
      onAssistantMessage: (msg) => { if (isCurrent()) assistantMessage = msg },
      onError: (error) => { if (isCurrent()) streamingError.value = error },
    })
    if (isCurrent()) {
      const loaded = await fetchChatMessages(sessionId)
      if (isCurrent()) {
        messages.value = loaded
        loadedPersisted = true
      }
    }
  } catch (error) {
    if (!isCurrent()) return
    streamingError.value = error instanceof Error ? error.message : 'Unable to stream answer'
    if (assistantMessage) messages.value = [...messages.value, assistantMessage]
  } finally {
    if (isCurrent()) {
      streaming.value = false
      if (loadedPersisted || assistantMessage) streamingContent.value = ''
    }
  }
}

onMounted(async () => {
  if (publicAccess.value) {
    await initChat()
    return
  }
  await auth.initialize()
  if (auth.isAuthenticated) {
    await initChat()
  }
})
</script>

<template>
  <div class="embed-chat">
    <div v-if="!publicAccess && !auth.isReady" class="embed-chat__center">
      <AppSpinner compact label="Loading" />
    </div>

    <div v-else-if="!publicAccess && !auth.isAuthenticated" class="embed-chat__center">
      <VIcon icon="mdi-robot-outline" size="40" color="primary" class="mb-4" />
      <p class="embed-chat__hint">Sign in to access the documentation assistant.</p>
      <VBtn color="primary" @click="auth.login()">Sign in</VBtn>
    </div>

    <div v-else class="embed-chat__panel">
      <div class="embed-chat__header">
        <VIcon icon="mdi-robot-outline" size="16" color="primary" />
        <span>Documentation assistant</span>
      </div>

      <div v-if="!session" class="embed-chat__center">
        <AppSpinner compact label="Starting chat" />
      </div>
      <template v-else>
        <ChatMessages
          class="embed-chat__messages"
          :messages="messages"
          :streaming="streaming"
          :streaming-content="streamingContent"
          :streaming-error="streamingError"
        />
        <ChatComposer
          v-model="draftMessage"
          :clear-disabled="!hasChatContent()"
          :disabled="streaming"
          @clear-chat="clearChat"
          @submit="askQuestion"
        />
      </template>
    </div>
  </div>
</template>

<style scoped>
.embed-chat {
  display: flex;
  flex-direction: column;
  height: 100dvh;
  overflow: hidden;
  background: #ffffff;
}

.embed-chat__center {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 32px;
  text-align: center;
}

.embed-chat__hint {
  font-size: 14px;
  color: #5e6c84;
  margin-bottom: 16px;
}

.embed-chat__panel {
  display: grid;
  grid-template-rows: auto 1fr auto;
  height: 100%;
  overflow: hidden;
}

.embed-chat__header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 14px;
  border-bottom: 1px solid #dfe1e6;
  background: #f4f5f7;
  font-size: 14px;
  font-weight: 600;
  color: #172b4d;
  flex-shrink: 0;
}

.embed-chat__messages {
  min-height: 0;
  overflow-y: auto;
}
</style>
