<script setup lang="ts">
import ChatPanel from '../components/chat/ChatPanel.vue'
</script>

<template>
  <VContainer fluid class="pa-4">
    <div class="chat-heading">
      <h1>Documentation Chat</h1>
      <p class="muted-text">Ask questions grounded in synced Confluence documentation.</p>
    </div>
    <ChatPanel />
  </VContainer>
</template>

<style scoped>
.chat-heading {
  margin-bottom: 14px;
}

h1 {
  margin: 0;
  font-size: 24px;
  line-height: 32px;
}
</style>

