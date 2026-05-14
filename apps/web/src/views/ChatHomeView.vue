<script setup lang="ts">
import EmptyState from '../components/common/EmptyState.vue'
</script>

<template>
  <div class="chat-home">
    <EmptyState
      icon="mdi-robot-outline"
      title="Documentation assistant"
      message="Use the chat button at the bottom right to ask questions."
    />
  </div>
</template>

<style scoped>
.chat-home {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  min-height: calc(100dvh - 48px);
}

</style>
