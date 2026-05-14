<script setup lang="ts">
import { computed, nextTick, onMounted, useTemplateRef, watch } from 'vue'
import type { PageProposal } from '../../types/api'

interface EditChatMessage {
  id: number
  role: 'user' | 'assistant'
  content: string
}

const message = defineModel<string>({ default: '' })

const props = defineProps<{
  messages: EditChatMessage[]
  proposal?: PageProposal
  busy?: boolean
  busyLabel?: string
  disabled?: boolean
  applyingProposal?: boolean
  rejectingProposal?: boolean
}>()

const emit = defineEmits<{
  applyProposal: []
  rejectProposal: []
  submit: []
}>()

const messagesScroller = useTemplateRef<HTMLElement>('messagesScroller')
const awaitingProposalDecision = computed(() => props.proposal?.status === 'ready')
const promptDisabled = computed(() => Boolean(props.busy || props.disabled || awaitingProposalDecision.value))
const canSubmit = computed(() => !promptDisabled.value && message.value.trim().length > 0)
const lastAssistantMessageId = computed(() =>
  [...props.messages].reverse().find((chatMessage) => chatMessage.role === 'assistant')?.id,
)
const scrollContentKey = computed(() => {
  const lastMessage = props.messages.at(-1)
  return [
    props.messages.length,
    lastMessage?.id ?? '',
    lastMessage?.content.length ?? 0,
    props.proposal?.status ?? '',
    props.busy ? props.busyLabel ?? 'busy' : '',
  ].join(':')
})

/** Emits a prompt submission when the chat panel is not disabled or busy. */
function submitMessage(): void {
  if (!canSubmit.value) return
  emit('submit')
}

/** Scrolls the editor chat transcript to its newest message. */
function scrollToBottom(): void {
  const element = messagesScroller.value
  if (!element) return
  if (typeof element.scrollTo === 'function') {
    element.scrollTo({ top: element.scrollHeight })
  } else {
    element.scrollTop = element.scrollHeight
  }
}

watch(
  scrollContentKey,
  async () => {
    await nextTick()
    scrollToBottom()
  },
  { flush: 'post' },
)

onMounted(async () => {
  await nextTick()
  scrollToBottom()
})
</script>

<template>
  <aside class="edit-chat surface-border">
    <div class="edit-chat__header">
      <div>
        <div class="text-caption muted-text">LLM editor</div>
        <h2>AI Assistant</h2>
      </div>
      <div class="edit-chat__header-icon">
        <VIcon icon="mdi-creation" color="primary" size="20" />
      </div>
    </div>

    <div ref="messagesScroller" class="edit-chat__messages">
      <div v-if="messages.length === 0" class="edit-chat__empty">
        <div class="edit-chat__empty-card">
          <VIcon icon="mdi-creation" size="32" color="primary" class="mb-2" />
          <div class="text-subtitle-2 mb-1">AI Documentation Assistant</div>
          <div class="text-caption muted-text">Describe the change you want and the AI will draft it. Review, edit, and publish to Confluence.</div>
        </div>
      </div>
      <div
        v-for="chatMessage in messages"
        :key="chatMessage.id"
        :class="['edit-chat__message', `edit-chat__message--${chatMessage.role}`]"
      >
        <div class="edit-chat__message-role">
          <VIcon
            :icon="chatMessage.role === 'user' ? 'mdi-account-outline' : 'mdi-creation'"
            size="12"
          />
          {{ chatMessage.role === 'user' ? 'You' : 'Documentation assistant' }}
        </div>
        <p>{{ chatMessage.content }}</p>
      </div>

      <div v-if="busy" class="edit-chat__message edit-chat__message--assistant edit-chat__message--busy">
        <VProgressLinear indeterminate color="primary" height="2" rounded class="mb-2" />
        <div class="edit-chat__message-role">
          <VIcon icon="mdi-creation" size="12" />
          {{ busyLabel || 'Working' }}
        </div>
        <p class="text-caption muted-text mt-1 mb-0">This may take a moment…</p>
      </div>
    </div>

    <div v-if="awaitingProposalDecision" class="edit-chat__decision" data-testid="proposal-decision-actions">
      <div class="edit-chat__decision-inner">
        <div class="edit-chat__decision-heading">
          <VIcon icon="mdi-creation" size="16" color="primary" />
          <span class="text-body-2 font-weight-medium">Proposal ready</span>
        </div>
        <p v-if="props.proposal?.instruction" class="edit-chat__decision-excerpt muted-text text-caption">
          {{ props.proposal.instruction.slice(0, 120) }}{{ props.proposal.instruction.length > 120 ? '…' : '' }}
        </p>
        <div class="edit-chat__decision-actions">
          <VBtn
            color="error"
            variant="tonal"
            prepend-icon="mdi-close-circle-outline"
            block
            :disabled="props.busy || props.rejectingProposal"
            :loading="props.rejectingProposal"
            data-testid="reject-proposal-button"
            @click="emit('rejectProposal')"
          >
            Reject
          </VBtn>
          <VBtn
            color="primary"
            variant="flat"
            prepend-icon="mdi-check-circle"
            block
            :disabled="props.busy || props.applyingProposal"
            :loading="props.applyingProposal"
            data-testid="apply-proposal-button"
            @click="emit('applyProposal')"
          >
            Apply proposal
          </VBtn>
        </div>
      </div>
    </div>

    <form v-else class="edit-chat__composer" @submit.prevent="submitMessage">
      <VTextarea
        v-model="message"
        rows="1"
        :max-rows="4"
        auto-grow
        hide-details
        label="Ask for an edit..."
        :disabled="promptDisabled"
        @keydown.enter.exact.prevent="submitMessage"
      />
      <div class="edit-chat__composer-actions">
        <span class="edit-chat__composer-hint muted-text">⇧↵ New line</span>
        <VTooltip location="top" text="Send (Enter)">
          <template #activator="{ props: tp }">
            <VBtn
              v-bind="tp"
              class="edit-chat__send"
              type="submit"
              color="primary"
              :disabled="!canSubmit"
              aria-label="Send request"
              data-testid="send-edit-request-button"
            >
              <VIcon icon="mdi-send" size="18" />
            </VBtn>
          </template>
        </VTooltip>
      </div>
    </form>
  </aside>
</template>

<style scoped>
.edit-chat {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr) auto;
  min-width: 0;
  min-height: 0;
  height: 100%;
  max-height: 100%;
  overflow: hidden;
  border-radius: 8px;
  background: #ffffff;
}

.edit-chat__header {
  display: flex;
  gap: 10px;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px;
  border-bottom: 1px solid #dfe1e6;
}

.edit-chat__header h2 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  line-height: 24px;
}

.edit-chat__header-icon {
  display: grid;
  width: 34px;
  height: 34px;
  flex-shrink: 0;
  place-items: center;
  border: 1px solid #cce0ff;
  border-radius: 8px;
  background: #e9f2ff;
}

.edit-chat__messages {
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-height: 0;
  overflow: auto;
  padding: 12px;
}

.edit-chat__empty {
  display: flex;
  min-height: 180px;
  align-items: center;
  justify-content: center;
  padding: 8px;
}

.edit-chat__empty-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  padding: 20px 16px;
  border: 1px solid #cce0ff;
  border-radius: 10px;
  background: #f0f7ff;
  width: 100%;
}

.edit-chat__message {
  max-width: 90%;
  padding: 9px 12px;
  border: 1px solid #dfe1e6;
  border-radius: 4px 12px 12px 12px;
  background: #ffffff;
  box-shadow: 0 1px 3px rgba(9, 30, 66, 0.06);
}

.edit-chat__message--user {
  align-self: flex-end;
  border-color: #cce0ff;
  border-radius: 12px 12px 4px 12px;
  background: #e9f2ff;
  box-shadow: none;
}

.edit-chat__message--assistant {
  align-self: flex-start;
  background: #f8f9ff;
}

.edit-chat__message--busy {
  padding: 10px 14px;
  border-color: #dfe1e6;
  background: #f7f8fa;
  box-shadow: none;
}

.edit-chat__message-role {
  display: flex;
  gap: 4px;
  align-items: center;
  margin-bottom: 5px;
  color: #626f86;
  font-size: 11px;
  font-weight: 600;
  line-height: 16px;
  text-transform: uppercase;
  letter-spacing: 0.4px;
}

.edit-chat__message p {
  margin: 0;
  white-space: pre-wrap;
  font-size: 13px;
  line-height: 1.55;
}

.edit-chat__decision {
  padding: 12px;
  border-top: 1px solid #dfe1e6;
}

.edit-chat__decision-inner {
  padding: 12px;
  border: 1px solid #cce0ff;
  border-radius: 8px;
  background: #f0f7ff;
}

.edit-chat__decision-heading {
  display: flex;
  gap: 6px;
  align-items: center;
  margin-bottom: 6px;
}

.edit-chat__decision-excerpt {
  margin: 0 0 10px;
  line-height: 1.45;
}

.edit-chat__decision-actions {
  display: grid;
  grid-template-columns: minmax(0, 3fr) minmax(0, 7fr);
  gap: 8px;
}

.edit-chat__decision-button {
  min-width: 0;
}

.edit-chat__decision-button :deep(.v-btn__content) {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.edit-chat__composer {
  display: grid;
  grid-template-rows: auto auto;
  gap: 0;
  padding: 10px 12px 12px;
  border-top: 1px solid #dfe1e6;
}

.edit-chat__composer-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 6px;
}

.edit-chat__composer-hint {
  font-size: 11px;
}

.edit-chat__send {
  width: 36px;
  min-width: 36px;
  height: 36px;
  padding: 0;
  border-radius: 6px;
}
</style>
