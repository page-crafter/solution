import type { ChatMessage } from '../types/api'

export interface Citation {
  pageId?: number | null
  confluenceId?: string | null
  snippet?: string | null
  filePath?: string | null
  referenceId?: string | number | null
  title?: string | null
  webUrl?: string | null
}

export interface DisplayCitation extends Citation {
  href?: string
  label: string
}

export interface DisplayMessage extends ChatMessage {
  citations: DisplayCitation[]
  html: string
}

export type CitationLookup = Map<string, DisplayCitation>

/** Parses the API citation JSON into citation objects, dropping malformed entries. */
export function parseCitations(value: string): Citation[] {
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

/** Builds the visible label for a citation chip from the best available field. */
export function citationLabel(citation: Citation, index: number): string {
  if (citation.title) return citation.title
  if (citation.confluenceId) return `Confluence ${citation.confluenceId}`
  if (citation.filePath) return citation.filePath
  if (citation.referenceId) return `Reference ${citation.referenceId}`
  return `Reference ${index + 1}`
}

/** Builds the tooltip text for a citation chip. */
export function citationTitle(citation: Citation): string | undefined {
  return citation.snippet || citation.filePath || citation.webUrl || undefined
}

/** Returns a safe absolute http(s) URL or undefined for unsupported protocols. */
export function safeHttpHref(value?: string | null): string | undefined {
  if (!value) return undefined
  try {
    const url = new URL(value, window.location.origin)
    return ['http:', 'https:'].includes(url.protocol) ? url.href : undefined
  } catch {
    return undefined
  }
}

/** Escapes text before it is inserted into markdown-rendered HTML. */
export function escapeHtml(value: string): string {
  return value
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;')
}

/** Renders inline emphasis markers after the source text has been escaped. */
export function renderPlainInline(value: string): string {
  let html = escapeHtml(value)
  html = html.replace(/\*\*([^*\n]+)\*\*/g, '<strong>$1</strong>')
  html = html.replace(/__([^_\n]+)__/g, '<strong>$1</strong>')
  html = html.replace(/(^|[\s(])\*([^*\n]+)\*/g, '$1<em>$2</em>')
  html = html.replace(/(^|[\s(])_([^_\n]+)_/g, '$1<em>$2</em>')
  return html
}

/** Renders a sanitized anchor when the target URL is safe, otherwise plain text. */
export function renderLink(label: string, hrefValue: string): string {
  const href = safeHttpHref(hrefValue)
  if (!href) return renderPlainInline(label)
  return `<a href="${escapeHtml(href)}" target="_blank" rel="noopener noreferrer">${renderPlainInline(label)}</a>`
}

/** Extracts the lookup key from the app's raw confluence reference token. */
export function confluenceReferenceKey(value: string): string | undefined {
  const parts = value.split(':')
  return parts.length >= 3 ? parts.at(-1) : undefined
}

/** Renders a raw confluence reference as a citation link when the citation is known. */
export function renderConfluenceReference(value: string, citationLookup: CitationLookup): string {
  const citation = citationLookup.get(value) ?? citationLookup.get(confluenceReferenceKey(value) ?? '')
  if (!citation?.href) return renderPlainInline(value)
  return renderLink(citation.label, citation.href)
}

/** Renders the supported inline markdown subset used in streamed chat answers. */
export function renderInlineMarkdown(value: string, citationLookup: CitationLookup): string {
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

/** Renders a paragraph block while preserving markdown line breaks. */
export function renderParagraph(lines: string[], citationLookup: CitationLookup): string {
  return `<p>${renderInlineMarkdown(lines.join('\n'), citationLookup).replaceAll('\n', '<br>')}</p>`
}

/** Renders a markdown list block from already parsed list item text. */
export function renderList(items: string[], ordered: boolean, citationLookup: CitationLookup): string {
  const tag = ordered ? 'ol' : 'ul'
  const listItems = items.map((item) => `<li>${renderInlineMarkdown(item, citationLookup)}</li>`).join('')
  return `<${tag}>${listItems}</${tag}>`
}

/** Renders a blockquote using the same inline rules as normal paragraphs. */
export function renderBlockquote(lines: string[], citationLookup: CitationLookup): string {
  return `<blockquote>${renderParagraph(lines, citationLookup)}</blockquote>`
}

/** Renders a fenced code block with encoded text for the copy button handler. */
export function renderCodeBlock(lines: string[]): string {
  const code = lines.join('\n')
  const encodedCode = escapeHtml(encodeURIComponent(code))
  return [
    '<div class="code-block">',
    `<button type="button" class="code-copy-button" data-code="${encodedCode}" title="Copy code" aria-label="Copy code">Copy</button>`,
    `<pre><code>${escapeHtml(code)}</code></pre>`,
    '</div>',
  ].join('')
}

/** Renders the supported chat markdown block subset into safe HTML. */
export function renderMarkdown(content: string, citationLookup: CitationLookup = new Map()): string {
  const blocks: string[] = []
  const paragraph: string[] = []
  const listItems: string[] = []
  const quoteLines: string[] = []
  let listOrdered = false
  let codeLines: string[] | undefined

  /** Flushes accumulated paragraph lines into the output block list. */
  function flushParagraph(): void {
    if (!paragraph.length) return
    blocks.push(renderParagraph(paragraph, citationLookup))
    paragraph.length = 0
  }

  /** Flushes accumulated list items into the output block list. */
  function flushList(): void {
    if (!listItems.length) return
    blocks.push(renderList(listItems, listOrdered, citationLookup))
    listItems.length = 0
  }

  /** Flushes accumulated blockquote lines into the output block list. */
  function flushQuote(): void {
    if (!quoteLines.length) return
    blocks.push(renderBlockquote(quoteLines, citationLookup))
    quoteLines.length = 0
  }

  /** Flushes all currently open non-code block accumulators. */
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

/** Converts a raw citation into the display shape used by chat messages. */
export function toDisplayCitation(citation: Citation, index: number): DisplayCitation {
  return {
    ...citation,
    href: safeHttpHref(citation.webUrl),
    label: citationLabel(citation, index),
  }
}

/** Builds lookup aliases so inline confluence reference tokens can link to citations. */
export function buildCitationLookup(citations: DisplayCitation[]): CitationLookup {
  const lookup: CitationLookup = new Map()
  for (const citation of citations) {
    if (!citation.href) continue
    if (citation.confluenceId) lookup.set(String(citation.confluenceId), citation)
    if (citation.filePath) lookup.set(citation.filePath, citation)
  }
  return lookup
}

/** Decorates an API chat message with parsed citations and rendered HTML. */
export function toDisplayMessage(message: ChatMessage): DisplayMessage {
  const citations = parseCitations(message.citations_json).map(toDisplayCitation)
  return {
    ...message,
    citations,
    html: renderMarkdown(message.content, buildCitationLookup(citations)),
  }
}
