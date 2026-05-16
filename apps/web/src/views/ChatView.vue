<script setup lang="ts">
import AdminPageShell from '../components/common/AdminPageShell.vue'
import ChatPanel from '../components/chat/ChatPanel.vue'
</script>

<template>
  <AdminPageShell
    title="Documentation Chat"
    description="Ask questions grounded in synced Confluence documentation."
    fill
  >
    <ChatPanel />
  </AdminPageShell>
</template>
