<script setup lang="ts">
import { computed } from 'vue'
import { jobStatusColor, jobStatusIcon } from '../../utils/jobStatus'

const props = withDefaults(defineProps<{
  status?: string | null
  size?: 'x-small' | 'small' | 'default' | 'large' | 'x-large'
  variant?: 'flat' | 'text' | 'elevated' | 'tonal' | 'outlined' | 'plain'
  showIcon?: boolean
}>(), {
  status: undefined,
  size: 'small',
  variant: 'tonal',
  showIcon: true,
})

const color = computed(() => jobStatusColor(props.status))
const icon = computed(() => (props.showIcon ? jobStatusIcon(props.status) : undefined))
const label = computed(() => props.status ?? 'unknown')
</script>

<template>
  <VChip :color="color" :prepend-icon="icon" :size="size" :variant="variant">
    {{ label }}
  </VChip>
</template>
