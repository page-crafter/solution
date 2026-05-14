<script setup lang="ts">
import { computed, onMounted, shallowRef } from 'vue'
import { createChatSession, fetchChatMessages, streamChatQuestion } from '../../api/chat'
import { useChatSettings } from '../../composables/useChatSettings'
import type { ChatMessage, ChatSession } from '../../types/api'
import AppSpinner from './AppSpinner.vue'
import ChatComposer from '../chat/ChatComposer.vue'
import ChatMessages from '../chat/ChatMessages.vue'

const open = shallowRef(false)
const session = shallowRef<ChatSession>()
const messages = shallowRef<ChatMessage[]>([])
const draftMessage = shallowRef('')
const streamingContent = shallowRef('')
const streamingError = shallowRef('')
const streaming = shallowRef(false)
const chatGeneration = shallowRef(0)

const { snapshot } = useChatSettings()

const hasChatContent = computed(
  () =>
    messages.value.length > 0
    || streamingContent.value.length > 0
    || streamingError.value.length > 0,
)

/** Lazily creates a chat session and loads any persisted messages for the widget. */
async function initializeChat(): Promise<void> {
  if (session.value) return
  session.value = await createChatSession()
  const loaded = await fetchChatMessages(session.value.id)
  messages.value = loaded
}

/** Clears widget state and starts a fresh chat session. */
async function clearChat(): Promise<void> {
  chatGeneration.value += 1
  messages.value = []
  streamingContent.value = ''
  streamingError.value = ''
  streaming.value = false
  session.value = await createChatSession()
}

/** Streams one widget question while ignoring stale responses after resets. */
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

  /** Returns whether streamed callbacks still belong to the active widget session. */
  const isCurrentChat = () =>
    chatGeneration.value === requestGeneration && session.value?.id === sessionId

  let loadedPersistedMessages = false
  let assistantMessage: ChatMessage | undefined

  try {
    await streamChatQuestion(sessionId, message, snapshot(), {
      onDelta: (delta) => { if (isCurrentChat()) streamingContent.value += delta },
      onReferences: () => {},
      onStats: () => {},
      onAssistantMessage: (msg) => { if (isCurrentChat()) assistantMessage = msg },
      onError: (error) => {
        if (!isCurrentChat()) return
        streamingError.value = error
      },
    })
    if (isCurrentChat()) {
      const loaded = await fetchChatMessages(sessionId)
      if (isCurrentChat()) {
        messages.value = loaded
        loadedPersistedMessages = true
      }
    }
  } catch (error) {
    if (!isCurrentChat()) return
    streamingError.value = error instanceof Error ? error.message : 'Unable to stream answer'
    if (assistantMessage) messages.value = [...messages.value, assistantMessage]
  } finally {
    if (isCurrentChat()) {
      streaming.value = false
      if (loadedPersistedMessages || assistantMessage) streamingContent.value = ''
    }
  }
}

/** Opens or closes the floating chat widget panel. */
function toggleOpen(): void {
  open.value = !open.value
}

onMounted(initializeChat)
</script>

<template>
  <div class="chat-widget">
    <Transition name="chat-widget-panel">
      <div v-if="open" class="chat-widget__panel surface-border">
        <div class="chat-widget__panel-header">
          <div class="chat-widget__panel-title">
            <VIcon icon="mdi-robot-outline" size="16" color="primary" />
            <span>Documentation assistant</span>
          </div>
          <VBtn
            icon
            variant="text"
            size="small"
            density="compact"
            title="Close chat"
            aria-label="Close chat"
            @click="open = false"
          >
            <VIcon icon="mdi-close" size="18" />
          </VBtn>
        </div>

        <div v-if="!session" class="chat-widget__loading">
          <AppSpinner compact label="Starting chat" />
        </div>
        <template v-else>
          <ChatMessages
            class="chat-widget__messages"
            :messages="messages"
            :streaming="streaming"
            :streaming-content="streamingContent"
            :streaming-error="streamingError"
          />
          <ChatComposer
            v-model="draftMessage"
            :clear-disabled="!hasChatContent"
            :disabled="streaming"
            @clear-chat="clearChat"
            @submit="askQuestion"
          />
        </template>
      </div>
    </Transition>

    <VBtn
      class="chat-widget__fab"
      :color="open ? 'default' : 'primary'"
      :icon="open ? 'mdi-close' : 'mdi-message-text-outline'"
      size="large"
      elevation="4"
      :title="open ? 'Close chat' : 'Open documentation assistant'"
      :aria-label="open ? 'Close chat' : 'Open documentation assistant'"
      @click="toggleOpen"
    />
  </div>
</template>

<style scoped>
.chat-widget {
  position: fixed;
  right: 24px;
  bottom: 24px;
  z-index: 100;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 12px;
}

.chat-widget__fab {
  flex-shrink: 0;
}

.chat-widget__panel {
  display: grid;
  grid-template-rows: auto 1fr auto;
  width: min(400px, calc(100vw - 48px));
  height: min(520px, calc(100dvh - 120px));
  border-radius: 12px;
  background: #ffffff;
  box-shadow: 0 8px 32px rgba(9, 30, 66, 0.18), 0 2px 8px rgba(9, 30, 66, 0.1);
  overflow: hidden;
}

.chat-widget__panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px;
  border-bottom: 1px solid #dfe1e6;
  background: #f4f5f7;
  flex-shrink: 0;
}

.chat-widget__panel-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 600;
  color: #172b4d;
}

.chat-widget__loading {
  padding: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.chat-widget__messages {
  min-height: 0;
  overflow-y: auto;
}

.chat-widget-panel-enter-active,
.chat-widget-panel-leave-active {
  transition: opacity 0.18s ease, transform 0.18s ease;
}

.chat-widget-panel-enter-from,
.chat-widget-panel-leave-to {
  opacity: 0;
  transform: translateY(12px) scale(0.97);
}
</style>
