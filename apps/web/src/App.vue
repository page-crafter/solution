<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import EditorLayout from './layouts/EditorLayout.vue'
import EmbedLayout from './layouts/EmbedLayout.vue'
import EmptyLayout from './layouts/EmptyLayout.vue'
import WebsiteLayout from './layouts/WebsiteLayout.vue'

const route = useRoute()
const layout = computed(() => {
  if (route.meta.layout === 'empty') return EmptyLayout
  if (route.meta.layout === 'editor') return EditorLayout
  if (route.meta.layout === 'embed') return EmbedLayout
  if (route.meta.layout === 'website') return WebsiteLayout
  return null
})
</script>

<template>
  <VApp>
    <component v-if="layout" :is="layout">
      <RouterView />
    </component>
  </VApp>
</template>

