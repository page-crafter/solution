<script setup lang="ts">
import { computed, nextTick, onMounted, shallowRef, useTemplateRef, watch } from 'vue'
import type { ChatMessage } from '../../types/api'
import AppSpinner from '../common/AppSpinner.vue'

interface Citation {
  pageId?: number | null
  confluenceId?: string | null
  snippet?: string | null
  filePath?: string | null
  referenceId?: string | number | null
  title?: string | null
  webUrl?: string | null
}

interface DisplayCitation extends Citation {
  href?: string
  label: string
}

interface DisplayMessage extends ChatMessage {
  citations: DisplayCitation[]
  html: string
}

type CitationLookup = Map<string, DisplayCitation>

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

function parseCitations(value: string): Citation[] {
  try {
    const parsed = JSON.parse(value) as unknown
    return Array.isArray(parsed)
      ? parsed.filter((citation): citation is Citation => (
        typeof citation === 'object'
        && citation !== null
        && !Array.isArray(citation)
      ))
      : []
  } catch {
    return []
  }
}

function citationLabel(citation: Citation, index: number): string {
  if (citation.title) return citation.title
  if (citation.confluenceId) return `Confluence ${citation.confluenceId}`
  if (citation.filePath) return citation.filePath
  if (citation.referenceId) return `Reference ${citation.referenceId}`
  return `Reference ${index + 1}`
}

function citationTitle(citation: Citation): string | undefined {
  return citation.snippet || citation.filePath || citation.webUrl || undefined
}

function messageRoleLabel(role: ChatMessage['role']): string {
  return role === 'user' ? 'You' : 'Documentation assistant'
}

function messageAvatarIcon(role: ChatMessage['role']): string {
  return role === 'user' ? 'mdi-account-outline' : 'mdi-robot-outline'
}

function safeHttpHref(value?: string | null): string | undefined {
  if (!value) return undefined
  try {
    const url = new URL(value, window.location.origin)
    return ['http:', 'https:'].includes(url.protocol) ? url.href : undefined
  } catch {
    return undefined
  }
}

function escapeHtml(value: string): string {
  return value
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;')
}

function renderPlainInline(value: string): string {
  let html = escapeHtml(value)
  html = html.replace(/\*\*([^*\n]+)\*\*/g, '<strong>$1</strong>')
  html = html.replace(/__([^_\n]+)__/g, '<strong>$1</strong>')
  html = html.replace(/(^|[\s(])\*([^*\n]+)\*/g, '$1<em>$2</em>')
  html = html.replace(/(^|[\s(])_([^_\n]+)_/g, '$1<em>$2</em>')
  return html
}

function renderLink(label: string, hrefValue: string): string {
  const href = safeHttpHref(hrefValue)
  if (!href) return renderPlainInline(label)
  return `<a href="${escapeHtml(href)}" target="_blank" rel="noopener noreferrer">${renderPlainInline(label)}</a>`
}

function confluenceReferenceKey(value: string): string | undefined {
  const parts = value.split(':')
  return parts.length >= 3 ? parts.at(-1) : undefined
}

function renderConfluenceReference(value: string, citationLookup: CitationLookup): string {
  const citation = citationLookup.get(value) ?? citationLookup.get(confluenceReferenceKey(value) ?? '')
  if (!citation?.href) return renderPlainInline(value)
  return renderLink(citation.label, citation.href)
}

function renderInlineMarkdown(value: string, citationLookup: CitationLookup): string {
  const tokens = /(`[^`]+`|\[[^\]]+\]\([^)]+\)|https?:\/\/[^\s<]+|confluence:[A-Za-z0-9_-]+:[A-Za-z0-9_-]+)/g
  let html = ''
  let cursor = 0

  for (const match of value.matchAll(tokens)) {
    const token = match[0]
    const index = match.index ?? 0
    html += renderPlainInline(value.slice(cursor, index))

    if (token.startsWith('`')) {
      html += `<code>${escapeHtml(token.slice(1, -1))}</code>`
    } else if (token.startsWith('[')) {
      const linkMatch = /^\[([^\]]+)\]\(([^)]+)\)$/.exec(token)
      html += linkMatch ? renderLink(linkMatch[1], linkMatch[2]) : renderPlainInline(token)
    } else if (token.startsWith('confluence:')) {
      html += renderConfluenceReference(token, citationLookup)
    } else {
      html += renderLink(token, token)
    }

    cursor = index + token.length
  }

  html += renderPlainInline(value.slice(cursor))
  return html
}

function renderParagraph(lines: string[], citationLookup: CitationLookup): string {
  return `<p>${renderInlineMarkdown(lines.join('\n'), citationLookup).replaceAll('\n', '<br>')}</p>`
}

function renderList(items: string[], ordered: boolean, citationLookup: CitationLookup): string {
  const tag = ordered ? 'ol' : 'ul'
  const listItems = items.map((item) => `<li>${renderInlineMarkdown(item, citationLookup)}</li>`).join('')
  return `<${tag}>${listItems}</${tag}>`
}

function renderBlockquote(lines: string[], citationLookup: CitationLookup): string {
  return `<blockquote>${renderParagraph(lines, citationLookup)}</blockquote>`
}

function renderCodeBlock(lines: string[]): string {
  const code = lines.join('\n')
  const encodedCode = escapeHtml(encodeURIComponent(code))
  return [
    '<div class="code-block">',
    `<button type="button" class="code-copy-button" data-code="${encodedCode}" title="Copy code" aria-label="Copy code">Copy</button>`,
    `<pre><code>${escapeHtml(code)}</code></pre>`,
    '</div>',
  ].join('')
}

function renderMarkdown(content: string, citationLookup: CitationLookup = new Map()): string {
  const blocks: string[] = []
  const paragraph: string[] = []
  const listItems: string[] = []
  const quoteLines: string[] = []
  let listOrdered = false
  let codeLines: string[] | undefined

  function flushParagraph(): void {
    if (!paragraph.length) return
    blocks.push(renderParagraph(paragraph, citationLookup))
    paragraph.length = 0
  }

  function flushList(): void {
    if (!listItems.length) return
    blocks.push(renderList(listItems, listOrdered, citationLookup))
    listItems.length = 0
  }

  function flushQuote(): void {
    if (!quoteLines.length) return
    blocks.push(renderBlockquote(quoteLines, citationLookup))
    quoteLines.length = 0
  }

  function flushOpenBlocks(): void {
    flushParagraph()
    flushList()
    flushQuote()
  }

  for (const line of content.replaceAll('\r\n', '\n').split('\n')) {
    if (line.startsWith('```')) {
      if (codeLines) {
        blocks.push(renderCodeBlock(codeLines))
        codeLines = undefined
      } else {
        flushOpenBlocks()
        codeLines = []
      }
      continue
    }

    if (codeLines) {
      codeLines.push(line)
      continue
    }

    if (!line.trim()) {
      flushOpenBlocks()
      continue
    }

    const headingMatch = /^(#{1,6})\s+(.+)$/.exec(line)
    if (headingMatch) {
      flushOpenBlocks()
      const level = headingMatch[1].length
      blocks.push(`<h${level}>${renderInlineMarkdown(headingMatch[2], citationLookup)}</h${level}>`)
      continue
    }

    const orderedMatch = /^\s*\d+\.\s+(.+)$/.exec(line)
    const unorderedMatch = /^\s*[-*+]\s+(.+)$/.exec(line)
    if (orderedMatch || unorderedMatch) {
      flushParagraph()
      flushQuote()
      const nextOrdered = Boolean(orderedMatch)
      if (listItems.length && listOrdered !== nextOrdered) flushList()
      listOrdered = nextOrdered
      listItems.push((orderedMatch ?? unorderedMatch)?.[1] ?? '')
      continue
    }

    const quoteMatch = /^>\s?(.*)$/.exec(line)
    if (quoteMatch) {
      flushParagraph()
      flushList()
      quoteLines.push(quoteMatch[1])
      continue
    }

    flushList()
    flushQuote()
    paragraph.push(line)
  }

  if (codeLines) blocks.push(renderCodeBlock(codeLines))
  flushOpenBlocks()
  return blocks.join('\n')
}

function toDisplayCitation(citation: Citation, index: number): DisplayCitation {
  return {
    ...citation,
    href: safeHttpHref(citation.webUrl),
    label: citationLabel(citation, index),
  }
}

function citationLookup(citations: DisplayCitation[]): CitationLookup {
  const lookup: CitationLookup = new Map()
  for (const citation of citations) {
    if (!citation.href) continue
    if (citation.confluenceId) lookup.set(String(citation.confluenceId), citation)
    if (citation.filePath) lookup.set(citation.filePath, citation)
  }
  return lookup
}

const renderedMessages = computed<DisplayMessage[]>(() =>
  props.messages.map((message) => {
    const citations = parseCitations(message.citations_json).map(toDisplayCitation)
    return {
      ...message,
      citations,
      html: renderMarkdown(message.content, citationLookup(citations)),
    }
  }),
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

function isNearBottom(element: HTMLElement): boolean {
  return element.scrollHeight - element.scrollTop - element.clientHeight <= BOTTOM_SCROLL_THRESHOLD
}

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

function markUserScrollIntent(): void {
  userScrollIntent.value = true
}

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
    <div v-if="showsPlaceholder" class="placeholder">
      <div class="placeholder-content">
        <div class="placeholder-icon" aria-hidden="true">
          <VIcon icon="mdi-message-text-outline" size="34" color="primary" />
        </div>
        <div class="placeholder-title">Ask a question to begin</div>
        <div class="placeholder-copy">
          Answers are streamed from synced Confluence content.
        </div>
      </div>
    </div>

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

.placeholder {
  display: grid;
  flex: 1;
  min-height: 360px;
  place-items: center;
  text-align: center;
}

.placeholder-content {
  display: grid;
  justify-items: center;
  gap: 12px;
  max-width: 300px;
}

.placeholder-icon {
  display: grid;
  width: 72px;
  height: 72px;
  place-items: center;
  border: 1px solid #cce0ff;
  border-radius: 50%;
  background: #e9f2ff;
}

.placeholder-title {
  color: #172b4d;
  font-size: 17px;
  font-weight: 600;
  line-height: 24px;
}

.placeholder-copy {
  color: #626f86;
  font-size: 14px;
  line-height: 20px;
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
