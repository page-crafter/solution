<script setup lang="ts">
import { useRouter } from 'vue-router'
import ChatWidget from '../components/common/ChatWidget.vue'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const router = useRouter()
</script>

<template>
  <VAppBar height="48" flat border="b" class="editor-bar">
    <div class="editor-bar__brand">
      <VAvatar size="28" rounded="sm" color="primary">
        <VIcon icon="mdi-book-open-page-variant-outline" size="16" />
      </VAvatar>
      <span class="editor-bar__name">Documentation Hub</span>
    </div>
    <VSpacer />
    <VBtn
      v-if="auth.isAdmin"
      prepend-icon="mdi-cog-outline"
      variant="text"
      size="small"
      @click="router.push('/dashboard')"
    >
      Admin
    </VBtn>
    <VBtn prepend-icon="mdi-logout" variant="text" size="small" @click="auth.logout">
      Sign out
    </VBtn>
  </VAppBar>

  <VMain>
    <slot />
  </VMain>

  <ChatWidget />
</template>

<style scoped>
.editor-bar__brand {
  display: flex;
  gap: 10px;
  align-items: center;
  padding-left: 16px;
}

.editor-bar__name {
  font-size: 14px;
  font-weight: 700;
  letter-spacing: 0;
}
</style>
