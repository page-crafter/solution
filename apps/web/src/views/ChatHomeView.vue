<template>
  <div class="chat-home">
    <div class="chat-home__content">
      <VIcon icon="mdi-robot-outline" size="48" color="primary" class="mb-4" />
      <div class="text-h6 mb-2">Documentation assistant</div>
      <div class="text-body-2 text-medium-emphasis">Use the chat button at the bottom right to ask questions.</div>
    </div>
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

.chat-home__content {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  padding: 32px;
}
</style>
