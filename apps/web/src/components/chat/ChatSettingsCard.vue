<script setup lang="ts">
import type { ChatQueryMode, ChatQuerySettings } from '../../types/api'

type SettingKey = keyof ChatQuerySettings
type SettingValue = ChatQuerySettings[SettingKey]

const props = defineProps<{
  collapsed: boolean
  compact?: boolean
  disabled?: boolean
  settings: ChatQuerySettings
}>()

const emit = defineEmits<{
  resetAll: []
  resetSetting: [key: SettingKey]
  toggle: []
  updateSetting: [key: SettingKey, value: SettingValue]
}>()

const modeItems: Array<{ title: string, value: ChatQueryMode }> = [
  { title: 'Naive', value: 'naive' },
  { title: 'Local', value: 'local' },
  { title: 'Global', value: 'global' },
  { title: 'Hybrid', value: 'hybrid' },
  { title: 'Mix', value: 'mix' },
  { title: 'Bypass', value: 'bypass' },
]

const numericFields: Array<{ key: SettingKey, label: string, min: number }> = [
  { key: 'top_k', label: 'Top K', min: 1 },
  { key: 'chunk_top_k', label: 'Chunks', min: 1 },
  { key: 'max_entity_tokens', label: 'Entity', min: 1 },
  { key: 'max_relation_tokens', label: 'Relation', min: 1 },
  { key: 'max_total_tokens', label: 'Total', min: 1 },
]

function updateText(key: SettingKey, value: unknown): void {
  emit('updateSetting', key, String(value ?? ''))
}

function updateMode(value: unknown): void {
  emit('updateSetting', 'mode', value as ChatQueryMode)
}

function updateNumber(key: SettingKey, value: unknown): void {
  const nextValue = Number(value)
  emit('updateSetting', key, Number.isFinite(nextValue) && nextValue > 0 ? nextValue : 1)
}

function updateBoolean(key: SettingKey, value: unknown): void {
  emit('updateSetting', key, Boolean(value))
}
</script>

<template>
  <div :class="['settings-panel', { 'settings-panel--collapsed': collapsed }]">
    <VCard class="settings-card surface-border">
      <div
        v-if="collapsed"
        :class="['settings-rail', { 'settings-rail--compact': compact }]"
      >
        <VBtn
          icon="mdi-tune"
          size="small"
          variant="text"
          title="Open parameters"
          @click="emit('toggle')"
        />
        <div v-if="!compact" class="settings-rail__text">
          <div class="text-subtitle-2">Advanced</div>
          <div class="text-caption muted-text">Query parameters</div>
        </div>
        <VBtn
          v-if="!compact"
          icon="mdi-chevron-right"
          size="small"
          variant="text"
          title="Open parameters"
          @click="emit('toggle')"
        />
      </div>

      <template v-else>
        <div class="settings-header">
          <div class="settings-header__title">
            <VIcon icon="mdi-tune" size="18" />
            <div class="settings-header__text">
              <div class="text-subtitle-2">Advanced</div>
              <div class="text-caption muted-text">Query parameters</div>
            </div>
          </div>
          <div class="settings-header__actions">
            <VBtn
              icon="mdi-restore"
              size="small"
              variant="text"
              title="Reset all"
              :disabled="disabled"
              @click="emit('resetAll')"
            />
            <VBtn
              icon="mdi-chevron-right"
              size="small"
              variant="text"
              title="Collapse"
              @click="emit('toggle')"
            />
          </div>
        </div>

        <div class="settings-content">
          <div class="settings-field">
            <div class="settings-label">
              <span>User prompt</span>
              <VBtn
                icon="mdi-restore"
                size="x-small"
                variant="text"
                title="Reset user prompt"
                :disabled="disabled"
                @click="emit('resetSetting', 'user_prompt')"
              />
            </div>
            <VTextarea
              :model-value="props.settings.user_prompt"
              auto-grow
              density="compact"
              hide-details
              rows="1"
              max-rows="3"
              :disabled="disabled"
              @update:model-value="updateText('user_prompt', $event)"
            />
          </div>

          <div class="settings-field">
            <div class="settings-label">
              <span>Mode</span>
              <VBtn
                icon="mdi-restore"
                size="x-small"
                variant="text"
                title="Reset mode"
                :disabled="disabled"
                @click="emit('resetSetting', 'mode')"
              />
            </div>
            <VSelect
              :items="modeItems"
              :model-value="props.settings.mode"
              density="compact"
              hide-details
              :disabled="disabled"
              @update:model-value="updateMode"
            />
          </div>

          <div class="settings-number-grid">
            <div
              v-for="field in numericFields"
              :key="field.key"
              class="settings-field settings-field--number"
            >
              <div class="settings-label">
                <span>{{ field.label }}</span>
                <VBtn
                  icon="mdi-restore"
                  size="x-small"
                  variant="text"
                  :title="`Reset ${field.label}`"
                  :disabled="disabled"
                  @click="emit('resetSetting', field.key)"
                />
              </div>
              <VTextField
                :model-value="props.settings[field.key]"
                type="number"
                :min="field.min"
                density="compact"
                hide-details
                :disabled="disabled"
                @update:model-value="updateNumber(field.key, $event)"
              />
            </div>
          </div>

          <div class="settings-switches">
            <VSwitch
              class="settings-switch"
              :model-value="props.settings.enable_rerank"
              color="primary"
              density="compact"
              hide-details
              label="Rerank"
              :disabled="disabled"
              @update:model-value="updateBoolean('enable_rerank', $event)"
            />
            <VSwitch
              class="settings-switch"
              :model-value="props.settings.only_need_context"
              color="primary"
              density="compact"
              hide-details
              label="Context"
              :disabled="disabled"
              @update:model-value="updateBoolean('only_need_context', $event)"
            />
            <VSwitch
              class="settings-switch"
              :model-value="props.settings.only_need_prompt"
              color="primary"
              density="compact"
              hide-details
              label="Prompt"
              :disabled="disabled"
              @update:model-value="updateBoolean('only_need_prompt', $event)"
            />
          </div>
        </div>
      </template>
    </VCard>
  </div>
</template>

<style scoped>
.settings-panel {
  width: 100%;
  min-width: 0;
  min-height: 0;
}

.settings-panel--collapsed {
  flex: 0 0 auto;
}

.settings-card {
  height: 100%;
  overflow: hidden;
}

.settings-panel--collapsed .settings-card {
  height: 52px;
}

.settings-rail {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  gap: 8px;
  align-items: center;
  height: 100%;
  padding: 4px 8px;
}

.settings-rail--compact {
  grid-template-columns: 1fr;
  place-items: center;
}

.settings-rail__text {
  min-width: 0;
}

.settings-rail__text .text-subtitle-2,
.settings-rail__text .text-caption {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.settings-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 10px 10px 8px;
  border-bottom: 1px solid #dfe1e6;
}

.settings-header__title {
  display: grid;
  grid-template-columns: 22px minmax(0, 1fr);
  gap: 8px;
  align-items: center;
  min-width: 0;
}

.settings-header__text {
  min-width: 0;
}

.settings-header__text .text-subtitle-2,
.settings-header__text .text-caption {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.settings-header__actions {
  display: flex;
  gap: 2px;
}

.settings-content {
  display: flex;
  flex-direction: column;
  gap: 9px;
  height: calc(100% - 50px);
  padding: 10px;
  overflow: auto;
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

.settings-switches {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  column-gap: 14px;
  row-gap: 0;
  padding-top: 0;
}

.settings-switch {
  flex: 0 0 auto;
  min-width: 92px;
}

.settings-switches :deep(.v-input) {
  margin: 0;
}

.settings-switches :deep(.v-input__control) {
  min-height: 30px;
}

.settings-switches :deep(.v-selection-control) {
  min-height: 30px;
}

.settings-switches :deep(.v-selection-control__wrapper) {
  width: 40px;
  height: 30px;
}

.settings-switches :deep(.v-label) {
  margin-inline-start: 2px;
  font-size: 14px;
  line-height: 18px;
}

@media (max-width: 960px) {
  .settings-panel,
  .settings-panel--collapsed {
    width: 100%;
    min-width: 0;
  }

  .settings-card {
    height: auto;
    max-height: 70vh;
  }

  .settings-rail {
    align-items: center;
    height: 48px;
    padding: 4px 8px;
  }
}
</style>
