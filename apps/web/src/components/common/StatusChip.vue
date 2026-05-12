<script setup lang="ts">
import { computed } from 'vue'
import type { DraftState } from '../../types/api'

const props = defineProps<{
  state: DraftState | string
}>()

const color = computed(() => {
  if (props.state === 'Published') return 'success'
  if (props.state === 'Preview ready') return 'primary'
  if (props.state === 'Publish blocked') return 'error'
  return 'secondary'
})
</script>

<template>
  <VChip :color="color" size="small" variant="tonal">
    {{ state }}
  </VChip>
</template>
