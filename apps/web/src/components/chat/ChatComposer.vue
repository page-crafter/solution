<script setup lang="ts">
import { computed } from 'vue'

const message = defineModel<string>({ required: true })

const props = defineProps<{
  clearDisabled?: boolean
  disabled?: boolean
}>()

const emit = defineEmits<{
  clearChat: []
  submit: []
}>()

const canSubmit = computed(() => !props.disabled && message.value.trim().length > 0)
const canClearChat = computed(() => !props.clearDisabled)

/** Requests a parent-level chat reset without mutating the local draft input. */
function clearChat(): void {
  if (!canClearChat.value) return
  emit('clearChat')
}

/** Emits submit when the draft has content and the parent has not disabled sending. */
function submitMessage(): void {
  if (!canSubmit.value) return
  emit('submit')
}
</script>

<template>
  <form class="chat-composer" @submit.prevent="submitMessage">
    <VTextarea
      v-model="message"
      auto-grow
      class="chat-composer__input"
      hide-details
      label="Ask about the documentation"
      max-rows="4"
      rows="1"
      :disabled="disabled"
      @keydown.enter.exact.prevent="submitMessage"
    />
    <div class="chat-composer__actions">
      <VBtn
        class="chat-composer__button chat-composer__button--clear"
        type="button"
        variant="tonal"
        :disabled="!canClearChat"
        title="Clear chat"
        aria-label="Clear chat"
        data-testid="clear-chat-button"
        @click.prevent.stop="clearChat"
      >
        <VIcon icon="mdi-delete-outline" size="19" />
      </VBtn>
      <VBtn
        class="chat-composer__button chat-composer__button--send"
        type="submit"
        color="primary"
        variant="flat"
        :disabled="!canSubmit"
        title="Send message"
        aria-label="Send message"
        data-testid="send-message-button"
      >
        <VIcon icon="mdi-send" size="20" />
      </VBtn>
    </div>
  </form>
</template>

<style scoped>
.chat-composer {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 10px;
  align-items: end;
  padding: 12px;
  border-top: 1px solid #dfe1e6;
  background: #ffffff;
}

.chat-composer__input {
  min-width: 0;
}

.chat-composer__actions {
  display: flex;
  gap: 8px;
  align-items: end;
}

.chat-composer__button {
  width: 40px;
  min-width: 40px;
  height: 40px;
  padding: 0;
  border-radius: 6px;
}

.chat-composer__button--clear {
  border: 1px solid #dfe1e6;
  color: #44546f;
}

.chat-composer__button--send {
  box-shadow: 0 1px 2px rgba(9, 30, 66, 0.18);
}

.chat-composer__button--send:not(.v-btn--disabled):hover {
  background: #0055cc;
}
</style>
