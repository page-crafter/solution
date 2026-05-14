import { reactive, readonly, watch } from 'vue'
import type { ChatQuerySettings } from '../types/api'

const STORAGE_KEY = 'page-crafter:chat-settings'

export const defaultChatSettings: ChatQuerySettings = {
  mode: 'mix',
  user_prompt: '',
  top_k: 40,
  chunk_top_k: 20,
  max_entity_tokens: 6000,
  max_relation_tokens: 8000,
  max_total_tokens: 30000,
  enable_rerank: true,
  only_need_context: false,
  only_need_prompt: false,
}

/** Loads persisted chat settings from localStorage and ignores unknown keys. */
function loadStoredSettings(): Partial<ChatQuerySettings> {
  const rawValue = window.localStorage.getItem(STORAGE_KEY)
  if (!rawValue) return {}
  try {
    const parsed = JSON.parse(rawValue) as Record<string, unknown>
    return Object.fromEntries(
      Object.keys(defaultChatSettings)
        .filter((key) => key in parsed)
        .map((key) => [key, parsed[key]]),
    ) as Partial<ChatQuerySettings>
  } catch {
    return {}
  }
}

/** Persists the current chat settings snapshot into localStorage. */
function persistSettings(settings: ChatQuerySettings): void {
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(settings))
}

/** Provides reactive chat query settings with reset and persistence helpers. */
export function useChatSettings() {
  const settings = reactive<ChatQuerySettings>({
    ...defaultChatSettings,
    ...loadStoredSettings(),
  })

  /** Updates one chat setting and enforces mutually exclusive context/prompt flags. */
  function updateSetting<Key extends keyof ChatQuerySettings>(
    key: Key,
    value: ChatQuerySettings[Key],
  ): void {
    settings[key] = value
    if (key === 'only_need_context' && value === true) {
      settings.only_need_prompt = false
    }
    if (key === 'only_need_prompt' && value === true) {
      settings.only_need_context = false
    }
  }

  /** Resets one chat setting back to the shared default value. */
  function resetSetting(key: keyof ChatQuerySettings): void {
    updateSetting(key, defaultChatSettings[key] as never)
  }

  /** Resets every chat setting back to the shared defaults. */
  function resetAll(): void {
    for (const key of Object.keys(defaultChatSettings) as Array<keyof ChatQuerySettings>) {
      updateSetting(key, defaultChatSettings[key] as never)
    }
  }

  /** Returns a plain object snapshot safe to send with an API request. */
  function snapshot(): ChatQuerySettings {
    return { ...settings }
  }

  watch(settings, () => persistSettings(settings), { deep: true })

  return {
    defaults: readonly(defaultChatSettings),
    resetAll,
    resetSetting,
    settings,
    snapshot,
    updateSetting,
  }
}
