import type { ConfluencePage } from '../types/api'

/** Builds a breadcrumb-like page path from a page and the loaded page tree. */
export function buildPagePath(page: ConfluencePage, allPages: ConfluencePage[]): string {
  const titles = [page.title]
  let parentId = page.parent_confluence_id
  const seen = new Set<string>()

  while (parentId && !seen.has(parentId)) {
    seen.add(parentId)
    const parent = allPages.find((candidate) => candidate.confluence_id === parentId)
    if (!parent) return titles.join(' / ')
    titles.unshift(parent.title)
    parentId = parent.parent_confluence_id
  }

  return titles.join(' / ')
}
