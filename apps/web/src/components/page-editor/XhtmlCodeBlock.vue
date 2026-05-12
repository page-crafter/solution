<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  code: string
  label?: string
}>()

function attributeText(element: Element): string {
  return Array.from(element.attributes)
    .map((attribute) => `${attribute.name}="${attribute.value}"`)
    .join(' ')
}

function fallbackFormat(source: string): string {
  return source.trim().replace(/></g, '>\n<')
}

function serializeNode(node: ChildNode, depth: number): string {
  const indent = '  '.repeat(depth)
  if (node.nodeType === Node.TEXT_NODE) {
    return `${indent}${node.textContent?.trim() ?? ''}`.trimEnd()
  }
  if (node.nodeType !== Node.ELEMENT_NODE) {
    return `${indent}${new XMLSerializer().serializeToString(node).trim()}`
  }

  const element = node as Element
  const attributes = attributeText(element)
  const tagName = element.tagName
  const openTag = attributes ? `<${tagName} ${attributes}>` : `<${tagName}>`

  if (element.childNodes.length === 0) {
    return attributes ? `${indent}<${tagName} ${attributes}/>` : `${indent}<${tagName}/>`
  }

  if (element.childNodes.length === 1 && element.firstChild?.nodeType === Node.TEXT_NODE) {
    return `${indent}${openTag}${element.textContent ?? ''}</${tagName}>`
  }

  const children = Array.from(element.childNodes)
    .map((child) => serializeNode(child, depth + 1))
    .filter((line) => line.trim().length > 0)
    .join('\n')

  return `${indent}${openTag}\n${children}\n${indent}</${tagName}>`
}

function formatStorageXhtml(source: string): string {
  const trimmed = source.trim()
  if (!trimmed) return ''
  const document = new DOMParser().parseFromString(
    `<root xmlns:ac="http://atlassian.com/content" xmlns:ri="http://atlassian.com/resource/identifier">${trimmed}</root>`,
    'application/xml',
  )
  if (document.querySelector('parsererror')) return fallbackFormat(trimmed)
  return Array.from(document.documentElement.childNodes)
    .map((node) => serializeNode(node, 0))
    .filter((line) => line.trim().length > 0)
    .join('\n')
}

const formattedCode = computed(() => formatStorageXhtml(props.code))
</script>

<template>
  <div class="xhtml-code">
    <div class="xhtml-code__header">
      <VIcon icon="mdi-code-tags" color="primary" />
      <span>{{ label ?? 'Storage XHTML' }}</span>
    </div>
    <pre class="xhtml-code__body"><code>{{ formattedCode }}</code></pre>
  </div>
</template>

<style scoped>
.xhtml-code {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  min-height: 560px;
  max-height: calc(100vh - 220px);
  max-height: calc(100dvh - 220px);
  overflow: hidden;
  border: 1px solid #dfe1e6;
  border-radius: 8px;
  background: #ffffff;
}

.xhtml-code__header {
  display: flex;
  gap: 8px;
  align-items: center;
  min-height: 42px;
  padding: 8px 12px;
  border-bottom: 1px solid #dfe1e6;
  color: #44546f;
  font-size: 13px;
  line-height: 18px;
}

.xhtml-code__body {
  min-height: 0;
  margin: 0;
  overflow: auto;
  padding: 16px;
  color: #172b4d;
  background: #f7f8fa;
  font-family: "SFMono-Regular", Consolas, "Liberation Mono", monospace;
  font-size: 12px;
  line-height: 18px;
  white-space: pre-wrap;
  word-break: break-word;
}
</style>
