<script setup lang="ts">
import { computed } from 'vue'

type ValidationTone = 'default' | 'primary' | 'warning' | 'danger'

interface ToneConfig {
  color: string
  icon: string
}

const isOpen = defineModel<boolean>({ default: false })

const props = withDefaults(defineProps<{
  title: string
  message: string
  supportingText?: string
  confirmLabel?: string
  cancelLabel?: string
  tone?: ValidationTone
  icon?: string
  loading?: boolean
  disabled?: boolean
  persistent?: boolean
  maxWidth?: number | string
}>(), {
  supportingText: undefined,
  confirmLabel: 'Confirm',
  cancelLabel: 'Cancel',
  tone: 'default',
  icon: undefined,
  loading: false,
  disabled: false,
  persistent: false,
  maxWidth: 460,
})

const emit = defineEmits<{
  cancel: []
  confirm: []
}>()

const toneConfig = computed<ToneConfig>(() => {
  if (props.tone === 'danger') {
    return { color: 'error', icon: 'mdi-alert-outline' }
  }
  if (props.tone === 'warning') {
    return { color: 'warning', icon: 'mdi-alert-circle-outline' }
  }
  if (props.tone === 'primary') {
    return { color: 'primary', icon: 'mdi-check-circle-outline' }
  }
  return { color: 'secondary', icon: 'mdi-help-circle-outline' }
})

const resolvedColor = computed(() => toneConfig.value.color)
const resolvedIcon = computed(() => props.icon ?? toneConfig.value.icon)
const isPersistent = computed(() => props.persistent || props.loading)

function cancel(): void {
  if (props.loading) return
  isOpen.value = false
  emit('cancel')
}
</script>

<template>
  <VDialog
    v-model="isOpen"
    :max-width="maxWidth"
    :persistent="isPersistent"
  >
    <VCard class="action-validation-card surface-border">
      <VCardText class="action-validation-body">
        <div class="action-validation-icon" :class="`action-validation-icon--${resolvedColor}`">
          <VIcon :icon="resolvedIcon" :color="resolvedColor" size="30" />
        </div>

        <div class="action-validation-copy">
          <h2>{{ title }}</h2>
          <p>{{ message }}</p>
          <p v-if="supportingText" class="muted-text">{{ supportingText }}</p>
        </div>
      </VCardText>

      <VCardActions class="action-validation-actions">
        <VBtn
          variant="text"
          :disabled="loading"
          @click="cancel"
        >
          {{ cancelLabel }}
        </VBtn>
        <VBtn
          :color="resolvedColor"
          :loading="loading"
          :disabled="disabled"
          variant="flat"
          @click="emit('confirm')"
        >
          {{ confirmLabel }}
        </VBtn>
      </VCardActions>
    </VCard>
  </VDialog>
</template>

<style scoped>
.action-validation-card {
  border-radius: 8px;
}

.action-validation-body {
  display: grid;
  grid-template-columns: 44px minmax(0, 1fr);
  gap: 16px;
  padding: 22px 22px 12px;
}

.action-validation-icon {
  display: grid;
  width: 44px;
  height: 44px;
  place-items: center;
  border-radius: 8px;
  background: #f4f5f7;
}

.action-validation-icon--error {
  background: #ffebe6;
}

.action-validation-icon--primary {
  background: #e9f2ff;
}

.action-validation-icon--warning {
  background: #fff7d6;
}

.action-validation-copy {
  display: grid;
  gap: 8px;
  min-width: 0;
}

.action-validation-copy h2 {
  margin: 0;
  font-size: 18px;
  line-height: 24px;
}

.action-validation-copy p {
  margin: 0;
  line-height: 20px;
}

.action-validation-actions {
  padding: 8px 16px 16px;
}
</style>
