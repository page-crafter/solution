<script setup lang="ts">
import PageHeader from '../components/common/PageHeader.vue'
import ChatPanel from '../components/chat/ChatPanel.vue'
</script>

<template>
  <VContainer fluid class="pa-4">
    <PageHeader
      title="Documentation Chat"
      description="Ask questions grounded in synced Confluence documentation."
    />
    <ChatPanel />
  </VContainer>
</template>
