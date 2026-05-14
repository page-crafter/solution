/** Checks an HTML element tag name using Confluence storage's namespaced tags. */
export function isTag(element: Element, tagName: string): boolean {
  return element.tagName.toLowerCase() === tagName
}

/** Finds the first direct child with the requested tag name. */
export function childByTag(element: Element, tagName: string): Element | undefined {
  return Array.from(element.children).find((child) => isTag(child, tagName))
}

/** Converts Confluence storage macros into readable HTML placeholders for preview panes. */
export function normalizeConfluenceStorageHtml(storageHtml: string): string {
  const document = new DOMParser().parseFromString(`<main>${storageHtml}</main>`, 'text/html')
  const root = document.body.firstElementChild ?? document.body
  const macros = Array.from(root.querySelectorAll('*')).filter((element) =>
    isTag(element, 'ac:structured-macro'),
  )

  for (const macro of macros) {
    const macroName = macro.getAttribute('ac:name') ?? 'macro'
    const plainTextBody = childByTag(macro, 'ac:plain-text-body')
    const richTextBody = childByTag(macro, 'ac:rich-text-body')
    const bodyText = (plainTextBody?.textContent ?? richTextBody?.textContent ?? macro.textContent ?? '').trim()

    if (macroName === 'code') {
      const pre = document.createElement('pre')
      const code = document.createElement('code')
      code.textContent = bodyText
      pre.append(code)
      macro.replaceWith(pre)
      continue
    }

    const placeholder = document.createElement('span')
    placeholder.className = 'confluence-macro'
    placeholder.textContent = bodyText
      ? `[Confluence macro: ${macroName}] ${bodyText}`
      : `[Confluence macro: ${macroName}]`
    macro.replaceWith(placeholder)
  }

  return root.innerHTML
}
