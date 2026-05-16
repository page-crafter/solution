<script setup lang="ts">
import { computed, reactive, shallowRef } from 'vue'
import AdminPageShell from '../components/common/AdminPageShell.vue'
import CollapsiblePanel from '../components/common/CollapsiblePanel.vue'
import SectionCard from '../components/common/SectionCard.vue'
import { defaultChatSettings } from '../composables/useChatSettings'
import type { ChatQueryMode, ChatQuerySettings } from '../types/api'

type EmbedMode = 'iframe' | 'widget'
type WidgetPosition = 'bottom-right' | 'bottom-left' | 'top-right' | 'top-left'

const mode = shallowRef<EmbedMode>('iframe')
const embedCollapsed = shallowRef(false)
const widgetOptCollapsed = shallowRef(false)
const queryCollapsed = shallowRef(false)
const sidebarCollapsed = computed(() => embedCollapsed.value && widgetOptCollapsed.value && queryCollapsed.value)
const copied = shallowRef(false)

// — embed appearance
const width = shallowRef(400)
const height = shallowRef(600)
const borderRadius = shallowRef(12)

// — widget-only
const widgetPosition = shallowRef<WidgetPosition>('bottom-right')
const widgetBtnColor = shallowRef('#1976d2')

// — chat query params (mirrored from useChatSettings)
const chat = reactive<ChatQuerySettings>({ ...defaultChatSettings })

const origin = window.location.origin
const embedBase = `${origin}/embed/chat`

const modeItems: Array<{ title: string; value: ChatQueryMode }> = [
  { title: 'Naive', value: 'naive' },
  { title: 'Local', value: 'local' },
  { title: 'Global', value: 'global' },
  { title: 'Hybrid', value: 'hybrid' },
  { title: 'Mix', value: 'mix' },
  { title: 'Bypass', value: 'bypass' },
]

const positionItems: Array<{ title: string; value: WidgetPosition }> = [
  { title: 'Bottom right', value: 'bottom-right' },
  { title: 'Bottom left', value: 'bottom-left' },
  { title: 'Top right', value: 'top-right' },
  { title: 'Top left', value: 'top-left' },
]

const numericFields: Array<{ key: keyof ChatQuerySettings; label: string; min: number }> = [
  { key: 'top_k', label: 'Top K', min: 1 },
  { key: 'chunk_top_k', label: 'Chunks', min: 1 },
  { key: 'max_entity_tokens', label: 'Entity tokens', min: 1 },
  { key: 'max_relation_tokens', label: 'Relation tokens', min: 1 },
  { key: 'max_total_tokens', label: 'Total tokens', min: 1 },
]

const embedUrl = computed(() => {
  const params = new URLSearchParams()
  if (chat.mode !== defaultChatSettings.mode) params.set('mode', chat.mode)
  if (chat.user_prompt?.trim()) params.set('user_prompt', chat.user_prompt.trim())
  if (chat.top_k !== defaultChatSettings.top_k) params.set('top_k', String(chat.top_k))
  if (chat.chunk_top_k !== defaultChatSettings.chunk_top_k) params.set('chunk_top_k', String(chat.chunk_top_k))
  if (chat.max_entity_tokens !== defaultChatSettings.max_entity_tokens) params.set('max_entity_tokens', String(chat.max_entity_tokens))
  if (chat.max_relation_tokens !== defaultChatSettings.max_relation_tokens) params.set('max_relation_tokens', String(chat.max_relation_tokens))
  if (chat.max_total_tokens !== defaultChatSettings.max_total_tokens) params.set('max_total_tokens', String(chat.max_total_tokens))
  if (!chat.enable_rerank) params.set('enable_rerank', 'false')
  const qs = params.toString()
  return qs ? `${embedBase}?${qs}` : embedBase
})

/** Converts a widget corner choice into button and panel CSS fragments. */
function positionCss(pos: WidgetPosition): { btn: string; panel: string } {
  const isBottom = pos.startsWith('bottom')
  const isRight = pos.endsWith('right')
  const v = isBottom ? 'bottom' : 'top'
  const h = isRight ? 'right' : 'left'
  return {
    btn: `"${v}:24px", "${h}:24px"`,
    panel: `"${v}:92px", "${h}:24px"`,
  }
}

const iframeCode = computed(() =>
  `<iframe\n  src="${embedUrl.value}"\n  width="${width.value}"\n  height="${height.value}"\n  style="border:none;border-radius:${borderRadius.value}px;"\n  allow="clipboard-write"\n></iframe>`,
)

const widgetCode = computed(() => {
  const pos = positionCss(widgetPosition.value)
  return `<script>
(function () {
  var EMBED_URL = "${embedUrl.value}";
  var PANEL_W = ${width.value};
  var PANEL_H = ${height.value};
  var BTN_COLOR = "${widgetBtnColor.value}";
  var open = false;

  var btn = document.createElement("button");
  btn.setAttribute("aria-label", "Open documentation assistant");
  btn.style.cssText = [
    "position:fixed", ${pos.btn}, "z-index:9999",
    "width:56px", "height:56px", "border-radius:50%",
    "background:" + BTN_COLOR, "color:#fff", "border:none",
    "cursor:pointer", "box-shadow:0 4px 14px rgba(0,0,0,.25)",
    "display:flex", "align-items:center", "justify-content:center",
    "font-size:24px", "transition:background .2s",
  ].join(";");
  btn.innerHTML = "&#128172;";

  var panel = document.createElement("iframe");
  panel.src = EMBED_URL;
  panel.allow = "clipboard-write";
  panel.style.cssText = [
    "position:fixed", ${pos.panel}, "z-index:9998",
    "width:" + PANEL_W + "px", "height:" + PANEL_H + "px",
    "border:none", "border-radius:${borderRadius.value}px",
    "box-shadow:0 8px 32px rgba(9,30,66,.18)",
    "display:none", "background:#fff",
  ].join(";");

  btn.addEventListener("click", function () {
    open = !open;
    panel.style.display = open ? "block" : "none";
    btn.style.background = open ? "#424242" : BTN_COLOR;
    btn.innerHTML = open ? "&#10005;" : "&#128172;";
  });

  document.body.appendChild(panel);
  document.body.appendChild(btn);
})();
<\/script>`
})

const activeCode = computed(() => mode.value === 'iframe' ? iframeCode.value : widgetCode.value)

/** Copies the currently selected embed snippet and briefly shows copied feedback. */
async function copyCode(): Promise<void> {
  await navigator.clipboard.writeText(activeCode.value)
  copied.value = true
  setTimeout(() => { copied.value = false }, 2000)
}

/** Normalizes a positive numeric embed query setting from a form control. */
function updateNumber(key: keyof ChatQuerySettings, value: unknown): void {
  const n = Number(value)
  ;(chat as Record<string, unknown>)[key] = Number.isFinite(n) && n > 0 ? n : 1
}

/** Updates a boolean query option and keeps prompt/context-only options exclusive. */
function updateBoolean(key: keyof ChatQuerySettings, value: unknown): void {
  ;(chat as Record<string, unknown>)[key] = Boolean(value)
  if (key === 'only_need_context' && value) chat.only_need_prompt = false
  if (key === 'only_need_prompt' && value) chat.only_need_context = false
}

/** Restores default embed dimensions and border radius. */
function resetEmbed(): void {
  width.value = 400
  height.value = 600
  borderRadius.value = 12
}

/** Restores default widget position and button color. */
function resetWidget(): void {
  widgetPosition.value = 'bottom-right'
  widgetBtnColor.value = '#1976d2'
}

/** Restores advanced chat query parameters to the shared defaults. */
function resetQuery(): void {
  Object.assign(chat, defaultChatSettings)
}
</script>

<template>
  <AdminPageShell
    title="Integration"
    description="Embed the documentation assistant on any website."
  >
    <template #actions>
      <VBtnToggle
        v-model="mode"
        mandatory
        density="compact"
        variant="outlined"
        color="primary"
        rounded="lg"
      >
        <VBtn value="iframe" size="small">
          <VIcon icon="mdi-xml" size="16" class="mr-1" />
          iFrame
        </VBtn>
        <VBtn value="widget" size="small">
          <VIcon icon="mdi-message-badge-outline" size="16" class="mr-1" />
          Widget
        </VBtn>
      </VBtnToggle>
    </template>

    <!-- Embed URL bar -->
    <VCard class="surface-border embed-url-card mb-4" variant="flat">
      <div class="embed-url-row">
        <VIcon icon="mdi-link-variant" size="16" color="primary" />
        <span class="embed-url-label">Embed URL</span>
        <code class="embed-url-value">{{ embedUrl }}</code>
        <VChip size="x-small" color="success" variant="tonal" class="ml-auto">Active</VChip>
      </div>
    </VCard>

    <!-- Workspace -->
    <div class="integration-workspace">
      <!-- Code area -->
      <SectionCard
        :title="mode === 'iframe' ? 'iFrame embed' : 'Widget button'"
        :icon="mode === 'iframe' ? 'mdi-xml' : 'mdi-message-badge-outline'"
      >
          <p class="text-body-2 text-medium-emphasis mb-4">
            <template v-if="mode === 'iframe'">
              Drop an <code>&lt;iframe&gt;</code> anywhere in your HTML. Users authenticate via Keycloak inside the frame.
              Best results on the same domain as this app (avoids third-party cookie restrictions).
            </template>
            <template v-else>
              Paste this snippet before <code>&lt;/body&gt;</code>. Injects a floating chat button with no external
              dependencies. Auth is handled inside the panel.
            </template>
          </p>

          <div class="code-block surface-border">
            <div class="code-block__toolbar">
              <span class="code-block__lang">HTML</span>
              <VBtn
                size="small"
                variant="text"
                density="compact"
                :prepend-icon="copied ? 'mdi-check' : 'mdi-content-copy'"
                :color="copied ? 'success' : undefined"
                @click="copyCode"
              >
                {{ copied ? 'Copied' : 'Copy' }}
              </VBtn>
            </div>
            <pre class="code-block__pre"><code>{{ activeCode }}</code></pre>
          </div>
      </SectionCard>

      <!-- Settings sidebar -->
      <aside :class="['integration-sidebar', { 'integration-sidebar--collapsed': sidebarCollapsed }]">
        <CollapsiblePanel
          v-model:collapsed="embedCollapsed"
          icon="mdi-image-size-select-large"
          title="Embed"
          subtitle="Dimensions &amp; appearance"
          reset-title="Reset embed"
          expand-title="Open embed options"
          :compact="sidebarCollapsed"
          @reset="resetEmbed"
        >
          <div class="settings-section-label">Dimensions</div>
          <div class="settings-number-grid">
            <div class="settings-field">
              <div class="settings-label">Width (px)</div>
              <VTextField v-model.number="width" type="number" :min="200" density="compact" hide-details variant="outlined" />
            </div>
            <div class="settings-field">
              <div class="settings-label">Height (px)</div>
              <VTextField v-model.number="height" type="number" :min="300" density="compact" hide-details variant="outlined" />
            </div>
          </div>

          <div class="settings-field">
            <div class="settings-label">Border radius (px)</div>
            <VTextField v-model.number="borderRadius" type="number" :min="0" :max="24" density="compact" hide-details variant="outlined" />
          </div>
        </CollapsiblePanel>

        <CollapsiblePanel
          v-if="mode === 'widget'"
          v-model:collapsed="widgetOptCollapsed"
          icon="mdi-message-badge-outline"
          title="Widget button"
          subtitle="Position &amp; color"
          reset-title="Reset widget"
          expand-title="Open widget options"
          :compact="sidebarCollapsed"
          @reset="resetWidget"
        >
          <div class="settings-field">
            <div class="settings-label">Position</div>
            <VSelect v-model="widgetPosition" :items="positionItems" density="compact" hide-details variant="outlined" />
          </div>
          <div class="settings-field">
            <div class="settings-label">Button color</div>
            <div class="color-row">
              <input v-model="widgetBtnColor" type="color" class="color-picker" title="Pick button color" />
              <code class="color-value">{{ widgetBtnColor }}</code>
            </div>
          </div>
        </CollapsiblePanel>

        <CollapsiblePanel
          v-model:collapsed="queryCollapsed"
          icon="mdi-tune"
          title="Advanced"
          subtitle="Query parameters"
          reset-title="Reset query"
          expand-title="Open query parameters"
          :compact="sidebarCollapsed"
          @reset="resetQuery"
        >
          <div class="settings-field">
            <div class="settings-label">
              <span>User prompt</span>
              <VBtn icon="mdi-restore" size="x-small" variant="text" title="Reset" @click="chat.user_prompt = defaultChatSettings.user_prompt" />
            </div>
            <VTextarea v-model="chat.user_prompt" auto-grow density="compact" hide-details rows="1" max-rows="3" variant="outlined" />
          </div>

          <div class="settings-field">
            <div class="settings-label">
              <span>Mode</span>
              <VBtn icon="mdi-restore" size="x-small" variant="text" title="Reset" @click="chat.mode = defaultChatSettings.mode" />
            </div>
            <VSelect v-model="chat.mode" :items="modeItems" density="compact" hide-details variant="outlined" />
          </div>

          <div class="settings-number-grid">
            <div v-for="field in numericFields" :key="field.key" class="settings-field settings-field--number">
              <div class="settings-label">
                <span>{{ field.label }}</span>
                <VBtn icon="mdi-restore" size="x-small" variant="text" :title="`Reset ${field.label}`" @click="chat[field.key] = defaultChatSettings[field.key] as never" />
              </div>
              <VTextField :model-value="chat[field.key]" type="number" :min="field.min" density="compact" hide-details variant="outlined" @update:model-value="updateNumber(field.key, $event)" />
            </div>
            <div class="settings-field settings-field--number">
              <div class="settings-label">
                <span>Rerank</span>
                <VBtn icon="mdi-restore" size="x-small" variant="text" title="Reset" @click="chat.enable_rerank = defaultChatSettings.enable_rerank" />
              </div>
              <VSelect
                :model-value="chat.enable_rerank"
                :items="[{ title: 'Enabled', value: true }, { title: 'Disabled', value: false }]"
                density="compact"
                hide-details
                variant="outlined"
                @update:model-value="updateBoolean('enable_rerank', $event)"
              />
            </div>
          </div>
        </CollapsiblePanel>
      </aside>
    </div>

    <!-- Auth note -->
    <VAlert
      class="mt-4"
      type="info"
      variant="tonal"
      density="compact"
      icon="mdi-shield-key-outline"
    >
      <strong>Authentication</strong> — Both methods use Keycloak SSO.
      Users must have the <code>chat</code> or <code>admin</code> role.
      Without an active session, a sign-in prompt is shown inside the embed.
    </VAlert>
  </AdminPageShell>
</template>

<style scoped>
/* Embed URL bar */
.embed-url-card { border-radius: 8px; }

.embed-url-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 16px;
  flex-wrap: wrap;
}

.embed-url-label {
  font-size: 13px;
  font-weight: 500;
}

.embed-url-value {
  font-size: 12px;
  background: rgba(var(--v-theme-on-surface), 0.06);
  padding: 2px 6px;
  border-radius: 4px;
  word-break: break-all;
}

/* Workspace */
.integration-workspace {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 14px;
  align-items: start;
}

/* Sidebar */
.integration-sidebar {
  width: 292px;
  min-width: 292px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.integration-sidebar--collapsed {
  width: 56px;
  min-width: 56px;
}

.settings-section-label {
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.07em;
  color: var(--v-theme-on-surface);
  opacity: 0.4;
  padding-top: 2px;
}

.settings-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.settings-number-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.settings-field--number:last-child:nth-child(odd) {
  grid-column: 1 / -1;
}

.settings-label {
  display: flex;
  min-height: 20px;
  align-items: center;
  justify-content: space-between;
  gap: 4px;
  color: #44546f;
  font-size: 11px;
  font-weight: 600;
  line-height: 16px;
}

/* Color picker */
.color-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.color-picker {
  width: 36px;
  height: 36px;
  padding: 2px;
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 6px;
  cursor: pointer;
  background: none;
}

.color-value {
  font-size: 12px;
  background: rgba(var(--v-theme-on-surface), 0.06);
  padding: 2px 6px;
  border-radius: 4px;
}


/* Code block */
.code-block {
  border-radius: 8px;
  overflow: hidden;
  border-width: 1px;
  border-style: solid;
}

.code-block__toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 4px 4px 4px 14px;
  background: rgba(var(--v-theme-on-surface), 0.03);
  border-bottom: 1px solid rgba(var(--v-theme-on-surface), 0.08);
}

.code-block__lang {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  opacity: 0.45;
}

.code-block__pre {
  margin: 0;
  padding: 14px 16px;
  font-size: 12px;
  line-height: 1.65;
  overflow-x: auto;
  white-space: pre;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
}

@media (max-width: 960px) {
  .integration-workspace { grid-template-columns: 1fr; }

  .integration-sidebar,
  .integration-sidebar--collapsed {
    width: 100%;
    min-width: 0;
  }
}
</style>
