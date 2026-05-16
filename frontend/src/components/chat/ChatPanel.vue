<script setup lang="ts">
import { computed, onMounted, shallowRef } from 'vue'
import { createChatSession, fetchChatMessages, streamChatQuestion } from '../../api/chat'
import { useChatConversationStats } from '../../composables/useChatConversationStats'
import { useChatSettings } from '../../composables/useChatSettings'
import type { ChatMessage, ChatQuerySettings, ChatSession } from '../../types/api'
import AppSpinner from '../common/AppSpinner.vue'
import ChatComposer from './ChatComposer.vue'
import ChatMessages from './ChatMessages.vue'
import ChatSettingsCard from './ChatSettingsCard.vue'
import ChatStatsCard from './ChatStatsCard.vue'

type SidebarPanel = 'stats' | 'settings' | null

const session = shallowRef<ChatSession>()
const messages = shallowRef<ChatMessage[]>([])
const draftMessage = shallowRef('')
const streamingContent = shallowRef('')
const streamingError = shallowRef('')
const activeSidebarPanel = shallowRef<SidebarPanel>('stats')
const streaming = shallowRef(false)
const chatGeneration = shallowRef(0)

const {
  beginRequest,
  completeRequest,
  conversationStats,
  recordDelta,
  recordReferences,
  recordServerStats,
  recordStreamError,
  resetStats,
} = useChatConversationStats({ messages, streamingContent })

const {
  resetAll,
  resetSetting,
  settings,
  snapshot,
  updateSetting,
} = useChatSettings()

const hasChatContent = computed(
  () =>
    messages.value.length > 0
    || streamingContent.value.length > 0
    || streamingError.value.length > 0,
)

const statsCollapsed = computed(() => activeSidebarPanel.value !== 'stats')
const settingsCollapsed = computed(() => activeSidebarPanel.value !== 'settings')
const sidebarCollapsed = computed(() => activeSidebarPanel.value === null)

/** Creates the default documentation chat session. */
async function initializeChat(): Promise<void> {
  session.value = await createChatSession()
  await loadMessages()
}

/** Reloads messages from the current chat session. */
async function loadMessages(): Promise<void> {
  const sessionId = session.value?.id
  if (!sessionId) return

  const loadedMessages = await fetchChatMessages(sessionId)
  if (session.value?.id === sessionId) {
    messages.value = loadedMessages
  }
}

/** Adds the submitted user prompt immediately while the backend persists it. */
function appendOptimisticUserMessage(content: string): void {
  if (!session.value) return
  messages.value = [
    ...messages.value,
    {
      id: -Date.now(),
      session_id: session.value.id,
      role: 'user',
      content,
      citations_json: '[]',
    },
  ]
}

/** Persists one advanced chat setting change through the settings composable. */
function handleUpdateSetting<Key extends keyof ChatQuerySettings>(
  key: Key,
  value: ChatQuerySettings[Key],
): void {
  updateSetting(key, value)
}

/** Opens the stats sidebar panel or collapses it when it is already active. */
function toggleStatsPanel(): void {
  activeSidebarPanel.value = activeSidebarPanel.value === 'stats' ? null : 'stats'
}

/** Opens the settings sidebar panel or collapses it when it is already active. */
function toggleSettingsPanel(): void {
  activeSidebarPanel.value = activeSidebarPanel.value === 'settings' ? null : 'settings'
}

/** Streams an answer for the current question through the chat API. */
async function askQuestion(): Promise<void> {
  if (!session.value || streaming.value) return
  const message = draftMessage.value.trim()
  if (!message) return

  const sessionId = session.value.id
  const requestGeneration = chatGeneration.value
  appendOptimisticUserMessage(message)
  beginRequest()
  draftMessage.value = ''
  streaming.value = true
  streamingContent.value = ''
  streamingError.value = ''

  let assistantMessage: ChatMessage | undefined
  let loadedPersistedMessages = false
  /** Returns whether streamed callbacks still belong to the active chat session. */
  const isCurrentChat = () =>
    chatGeneration.value === requestGeneration && session.value?.id === sessionId

  try {
    await streamChatQuestion(
      sessionId,
      message,
      snapshot(),
      {
        onDelta: (delta) => {
          if (!isCurrentChat()) return
          streamingContent.value += delta
          recordDelta(delta)
        },
        onReferences: (references) => {
          if (!isCurrentChat()) return
          recordReferences(references)
        },
        onStats: (stats) => {
          if (!isCurrentChat()) return
          recordServerStats(stats)
        },
        onAssistantMessage: (message) => {
          if (!isCurrentChat()) return
          assistantMessage = message
        },
        onError: (error) => {
          if (!isCurrentChat()) return
          streamingError.value = error
          recordStreamError(error)
        },
      },
    )
    if (isCurrentChat()) {
      await loadMessages()
      loadedPersistedMessages = true
    }
  } catch (error) {
    if (!isCurrentChat()) return
    streamingError.value = error instanceof Error ? error.message : 'Unable to stream answer'
    recordStreamError(streamingError.value)
    if (assistantMessage) {
      messages.value = [...messages.value, assistantMessage]
    }
  } finally {
    if (isCurrentChat()) {
      streaming.value = false
      if (!streamingError.value) {
        completeRequest()
      }
      if (loadedPersistedMessages || assistantMessage) {
        streamingContent.value = ''
      }
    }
  }
}

/** Resets the current chat UI and starts a fresh session while preserving settings. */
async function clearChat(): Promise<void> {
  chatGeneration.value += 1
  messages.value = []
  streamingContent.value = ''
  streamingError.value = ''
  streaming.value = false
  resetStats()
  session.value = await createChatSession()
}

onMounted(async () => {
  await initializeChat()
})
</script>

<template>
  <div class="chat-workspace">
    <VCard class="chat-panel surface-border">
      <div v-if="!session" class="chat-panel__loading">
        <AppSpinner compact label="Starting documentation chat" />
      </div>
      <template v-else>
        <ChatMessages
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
    </VCard>

    <aside :class="['chat-sidebar', { 'chat-sidebar--collapsed': sidebarCollapsed }]">
      <ChatStatsCard
        :compact="sidebarCollapsed"
        :collapsed="statsCollapsed"
        :stats="conversationStats"
        @toggle="toggleStatsPanel"
      />
      <ChatSettingsCard
        :compact="sidebarCollapsed"
        :collapsed="settingsCollapsed"
        :disabled="streaming"
        :settings="settings"
        @reset-all="resetAll"
        @reset-setting="resetSetting"
        @toggle="toggleSettingsPanel"
        @update-setting="handleUpdateSetting"
      />
    </aside>
  </div>
</template>

<style scoped>
.chat-workspace {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 14px;
  align-items: stretch;
  flex: 1 1 auto;
  height: 100%;
  min-height: 0;
}

.chat-panel {
  display: grid;
  grid-template-rows: 1fr auto;
  height: 100%;
  max-height: 100%;
  min-height: 0;
  overflow: hidden;
}

.chat-panel__loading {
  padding: 24px;
}

.chat-sidebar {
  display: flex;
  flex-direction: column;
  gap: 14px;
  width: 292px;
  min-width: 292px;
  max-height: 100%;
  min-height: 0;
  overflow: hidden;
}

.chat-sidebar--collapsed {
  width: 56px;
  min-width: 56px;
}

@media (max-width: 960px) {
  .chat-workspace {
    grid-template-columns: 1fr;
  }

  .chat-panel {
    height: min(64dvh, 100%);
    max-height: 100%;
  }

  .chat-sidebar {
    width: 100%;
    min-width: 0;
    max-height: none;
    overflow: visible;
  }

  .chat-sidebar--collapsed {
    width: 100%;
    min-width: 0;
  }
}
</style>
