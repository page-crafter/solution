<script setup lang="ts">
import { computed, nextTick, onMounted, shallowRef, useTemplateRef, watch } from 'vue'
import type { ChatMessage } from '../../types/api'
import { citationTitle, renderMarkdown, toDisplayMessage } from '../../utils/chatMarkdown'
import type { DisplayMessage } from '../../utils/chatMarkdown'
import AppSpinner from '../common/AppSpinner.vue'
import EmptyState from '../common/EmptyState.vue'

const props = defineProps<{
  messages: ChatMessage[]
  streamingContent?: string
  streamingError?: string
  streaming?: boolean
}>()

const BOTTOM_SCROLL_THRESHOLD = 48
const COPY_BUTTON_RESET_MS = 1400
const messagesScroller = useTemplateRef<HTMLElement>('messagesScroller')
const autoScrollEnabled = shallowRef(true)
const userScrollIntent = shallowRef(false)
const copyResetTimers = new WeakMap<HTMLButtonElement, number>()

/** Maps a persisted chat role to the label shown above each message. */
function messageRoleLabel(role: ChatMessage['role']): string {
  return role === 'user' ? 'You' : 'Documentation assistant'
}

/** Maps a persisted chat role to the avatar icon shown beside each message. */
function messageAvatarIcon(role: ChatMessage['role']): string {
  return role === 'user' ? 'mdi-account-outline' : 'mdi-robot-outline'
}

const renderedMessages = computed<DisplayMessage[]>(() =>
  props.messages.map(toDisplayMessage),
)

const streamingHtml = computed(() => renderMarkdown(props.streamingContent ?? ''))

const scrollContentKey = computed(() => {
  const lastMessage = props.messages.at(-1)
  return [
    props.messages.length,
    lastMessage?.id ?? '',
    lastMessage?.content.length ?? 0,
    props.streamingContent?.length ?? 0,
    props.streamingError ?? '',
  ].join(':')
})

const showsPlaceholder = computed(
  () =>
    renderedMessages.value.length === 0
    && !props.streaming
    && !props.streamingContent
    && !props.streamingError,
)

/** Determines whether the message viewport is close enough to continue auto-scrolling. */
function isNearBottom(element: HTMLElement): boolean {
  return element.scrollHeight - element.scrollTop - element.clientHeight <= BOTTOM_SCROLL_THRESHOLD
}

/** Moves the message viewport to the latest content and re-enables auto-scroll. */
function scrollToBottom(): void {
  const element = messagesScroller.value
  if (!element) return
  if (typeof element.scrollTo === 'function') {
    element.scrollTo({ top: element.scrollHeight })
  } else {
    element.scrollTop = element.scrollHeight
  }
  autoScrollEnabled.value = true
  userScrollIntent.value = false
}

/** Records that a pointer, wheel, or touch event came from user scroll intent. */
function markUserScrollIntent(): void {
  userScrollIntent.value = true
}

/** Disables auto-scroll only after the user intentionally scrolls away from the bottom. */
function handleScroll(): void {
  const element = messagesScroller.value
  if (!element) return

  if (isNearBottom(element)) {
    autoScrollEnabled.value = true
    userScrollIntent.value = false
    return
  }

  if (userScrollIntent.value) {
    autoScrollEnabled.value = false
  }
}

/** Copies text to the clipboard with a textarea fallback for older browsers. */
function copyTextToClipboard(value: string): Promise<void> {
  if (navigator.clipboard?.writeText) {
    return navigator.clipboard.writeText(value)
  }

  const textarea = document.createElement('textarea')
  textarea.value = value
  textarea.setAttribute('readonly', '')
  textarea.style.position = 'fixed'
  textarea.style.opacity = '0'
  document.body.appendChild(textarea)
  textarea.select()
  document.execCommand('copy')
  textarea.remove()
  return Promise.resolve()
}

/** Copies one rendered code block and temporarily updates its button state. */
async function copyCodeBlock(button: HTMLButtonElement): Promise<void> {
  const encodedCode = button.dataset.code
  if (!encodedCode) return

  window.clearTimeout(copyResetTimers.get(button))
  const originalLabel = button.dataset.label ?? button.textContent ?? 'Copy'
  button.dataset.label = originalLabel
  button.disabled = true

  try {
    await copyTextToClipboard(decodeURIComponent(encodedCode))
    button.textContent = 'Copied'
    button.classList.add('code-copy-button--copied')
  } catch {
    button.textContent = 'Failed'
  }

  const timer = window.setTimeout(() => {
    button.textContent = button.dataset.label ?? 'Copy'
    button.classList.remove('code-copy-button--copied')
    button.disabled = false
  }, COPY_BUTTON_RESET_MS)
  copyResetTimers.set(button, timer)
}

/** Handles delegated clicks from rendered markdown code copy buttons. */
function handleMessageClick(event: MouseEvent): void {
  if (!(event.target instanceof Element)) return
  const copyButton = event.target.closest<HTMLButtonElement>('.code-copy-button')
  if (!copyButton) return
  void copyCodeBlock(copyButton)
}

watch(
  scrollContentKey,
  async () => {
    await nextTick()
    if (autoScrollEnabled.value) {
      scrollToBottom()
    }
  },
  { flush: 'post' },
)

onMounted(async () => {
  await nextTick()
  scrollToBottom()
})
</script>

<template>
  <div
    ref="messagesScroller"
    class="chat-messages"
    @pointerdown.passive="markUserScrollIntent"
    @click="handleMessageClick"
    @scroll.passive="handleScroll"
    @touchstart.passive="markUserScrollIntent"
    @wheel.passive="markUserScrollIntent"
  >
    <EmptyState
      v-if="showsPlaceholder"
      icon="mdi-message-text-outline"
      title="Ask a question to begin"
      message="Answers are streamed from synced Confluence content."
      min-height="360px"
    />

    <div
      v-for="message in renderedMessages"
      :key="message.id"
      :class="['message', `message--${message.role}`]"
    >
      <VAvatar
        :class="['message__avatar', `message__avatar--${message.role}`]"
        size="32"
        :title="messageRoleLabel(message.role)"
      >
        <VIcon :icon="messageAvatarIcon(message.role)" size="18" />
      </VAvatar>
      <div class="message__bubble">
        <div class="message__role text-caption muted-text">
          {{ messageRoleLabel(message.role) }}
        </div>
        <div class="message__body" v-html="message.html" />
        <div v-if="message.citations.length" class="message__citations">
          <VChip
            v-for="(citation, index) in message.citations"
            :key="`${message.id}-${index}`"
            :href="citation.href"
            :link="Boolean(citation.href)"
            :rel="citation.href ? 'noopener noreferrer' : undefined"
            size="x-small"
            :target="citation.href ? '_blank' : undefined"
            variant="tonal"
            :title="citationTitle(citation)"
          >
            {{ citation.label }}
            <VIcon v-if="citation.href" end icon="mdi-open-in-new" size="12" />
          </VChip>
        </div>
      </div>
    </div>

    <div v-if="streaming || streamingContent || streamingError" class="message message--assistant">
      <VAvatar
        class="message__avatar message__avatar--assistant"
        size="32"
        title="Documentation assistant"
      >
        <VIcon icon="mdi-robot-outline" size="18" />
      </VAvatar>
      <div class="message__bubble">
        <div class="message__role text-caption muted-text">Documentation assistant</div>
        <div v-if="streamingContent" class="message__body" v-html="streamingHtml" />
        <AppSpinner v-else compact label="Searching synced documentation" />
        <VAlert
          v-if="streamingError"
          class="mt-2"
          density="compact"
          type="error"
          variant="tonal"
        >
          {{ streamingError }}
        </VAlert>
      </div>
    </div>
  </div>
</template>

<style scoped>
.chat-messages {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 0;
  padding: 18px;
  overflow-x: hidden;
  overflow-y: auto;
  overscroll-behavior: contain;
}

.message {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  width: min(100%, 780px);
  max-width: 780px;
  min-width: 0;
}

.message--user {
  align-self: flex-end;
  flex-direction: row-reverse;
}

.message--assistant {
  align-self: flex-start;
}

.message__avatar {
  flex: 0 0 auto;
  margin-top: 2px;
  border: 1px solid #dfe1e6;
}

.message__avatar--user {
  background: #0c66e4;
  color: #ffffff;
}

.message__avatar--assistant {
  background: #e9f2ff;
  color: #0c66e4;
}

.message__bubble {
  min-width: 0;
  max-width: min(738px, calc(100% - 42px));
  padding: 12px;
  border-radius: 8px;
  overflow-wrap: anywhere;
  word-break: break-word;
}

.message--user .message__bubble {
  background: #deebff;
}

.message--assistant .message__bubble {
  background: #f4f5f7;
}

.message__role {
  margin-bottom: 4px;
}

.message__body {
  min-width: 0;
  max-width: 100%;
  overflow-wrap: anywhere;
  line-height: 1.55;
  word-break: break-word;
}

.message__body :deep(p) {
  margin: 0 0 8px;
}

.message__body :deep(h1),
.message__body :deep(h2),
.message__body :deep(h3) {
  margin: 10px 0 6px;
  color: #172b4d;
  font-size: 16px;
  font-weight: 700;
  line-height: 22px;
}

.message__body :deep(h4),
.message__body :deep(h5),
.message__body :deep(h6) {
  margin: 8px 0 4px;
  color: #172b4d;
  font-size: 14px;
  font-weight: 700;
  line-height: 20px;
}

.message__body :deep(p:last-child),
.message__body :deep(ul:last-child),
.message__body :deep(ol:last-child),
.message__body :deep(pre:last-child),
.message__body :deep(blockquote:last-child),
.message__body :deep(h1:last-child),
.message__body :deep(h2:last-child),
.message__body :deep(h3:last-child),
.message__body :deep(h4:last-child),
.message__body :deep(h5:last-child),
.message__body :deep(h6:last-child) {
  margin-bottom: 0;
}

.message__body :deep(h1:first-child),
.message__body :deep(h2:first-child),
.message__body :deep(h3:first-child),
.message__body :deep(h4:first-child),
.message__body :deep(h5:first-child),
.message__body :deep(h6:first-child) {
  margin-top: 0;
}

.message__body :deep(ul),
.message__body :deep(ol) {
  margin: 6px 0 8px;
  padding-left: 22px;
}

.message__body :deep(li + li) {
  margin-top: 4px;
}

.message__body :deep(a) {
  color: #0c66e4;
  font-weight: 600;
  overflow-wrap: anywhere;
  text-decoration: none;
  word-break: break-word;
}

.message__body :deep(a:hover) {
  text-decoration: underline;
}

.message__body :deep(pre) {
  max-width: 100%;
  margin: 0;
  padding: 10px;
  overflow-x: hidden;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  border: 1px solid #dfe1e6;
  border-radius: 6px;
  background: #ffffff;
  word-break: break-word;
}

.message__body :deep(.code-block) {
  position: relative;
  max-width: 100%;
  margin: 8px 0;
  padding-top: 30px;
}

.message__body :deep(.code-block:last-child) {
  margin-bottom: 0;
}

.message__body :deep(.code-copy-button) {
  position: absolute;
  top: 0;
  right: 0;
  min-width: 58px;
  height: 24px;
  padding: 0 8px;
  border: 1px solid #dfe1e6;
  border-radius: 4px;
  background: #ffffff;
  color: #44546f;
  cursor: pointer;
  font-size: 12px;
  font-weight: 600;
  line-height: 22px;
}

.message__body :deep(.code-copy-button:hover) {
  border-color: #0c66e4;
  color: #0c66e4;
}

.message__body :deep(.code-copy-button:disabled) {
  cursor: default;
  opacity: 0.85;
}

.message__body :deep(.code-copy-button--copied) {
  border-color: #1f845a;
  color: #1f845a;
}

.message__body :deep(code) {
  border-radius: 4px;
  background: rgba(9, 30, 66, 0.08);
  font-family: "SFMono-Regular", Consolas, "Liberation Mono", monospace;
  font-size: 0.92em;
  overflow-wrap: anywhere;
  word-break: break-word;
}

.message__body :deep(pre code) {
  background: transparent;
}

.message__body :deep(blockquote) {
  margin: 8px 0;
  padding-left: 10px;
  border-left: 3px solid #0c66e4;
  color: #44546f;
}

.message__citations {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 10px;
  min-width: 0;
  max-width: 100%;
}

.message__citations :deep(.v-chip) {
  max-width: 100%;
}

.message__citations :deep(.v-chip__content) {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>
