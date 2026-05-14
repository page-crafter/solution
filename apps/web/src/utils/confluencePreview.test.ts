import { describe, expect, it } from 'vitest'
import { normalizeConfluenceStorageHtml } from './confluencePreview'

describe('confluencePreview utilities', () => {
  it('turns Confluence code macros into preformatted code', () => {
    const html = normalizeConfluenceStorageHtml(`
      <ac:structured-macro ac:name="code">
        <ac:plain-text-body>const value = 1</ac:plain-text-body>
      </ac:structured-macro>
    `)

    expect(html).toContain('<pre><code>const value = 1</code></pre>')
  })

  it('turns unknown macros into readable placeholders', () => {
    const html = normalizeConfluenceStorageHtml('<ac:structured-macro ac:name="toc"></ac:structured-macro>')

    expect(html).toContain('[Confluence macro: toc]')
  })
})
