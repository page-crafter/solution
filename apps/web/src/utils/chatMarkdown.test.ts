import { describe, expect, it } from 'vitest'
import { buildCitationLookup, parseCitations, renderMarkdown, toDisplayCitation, toDisplayMessage } from './chatMarkdown'
import type { ChatMessage } from '../types/api'

describe('chatMarkdown utilities', () => {
  it('renders the supported markdown subset as escaped HTML', () => {
    const html = renderMarkdown('**Bold**\n\n- Item\n\n<script>alert(1)</script>')

    expect(html).toContain('<strong>Bold</strong>')
    expect(html).toContain('<li>Item</li>')
    expect(html).toContain('&lt;script&gt;alert(1)&lt;/script&gt;')
  })

  it('links raw confluence references through citation lookup aliases', () => {
    const citation = toDisplayCitation({
      confluenceId: '123',
      title: 'Setup Guide',
      webUrl: 'https://docs.example.test/setup',
    }, 0)
    const html = renderMarkdown('See confluence:DOC:123', buildCitationLookup([citation]))

    expect(html).toContain('href="https://docs.example.test/setup"')
    expect(html).toContain('Setup Guide')
  })

  it('drops malformed citation payloads', () => {
    expect(parseCitations('not json')).toEqual([])
  })

  it('decorates persisted chat messages for display', () => {
    const message: ChatMessage = {
      id: 1,
      session_id: 'session-1',
      role: 'assistant',
      content: 'Answer',
      citations_json: '[]',
    }

    expect(toDisplayMessage(message).html).toBe('<p>Answer</p>')
  })
})
