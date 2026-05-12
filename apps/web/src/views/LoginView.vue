<script setup lang="ts">
import { useAuthStore } from '../stores/auth'
import ParticleBackground from '../components/common/ParticleBackground.vue'

const auth = useAuthStore()
</script>

<template>
  <div class="login-page">
    <ParticleBackground particle-color="#b0b8c4" :speed="0.4" :density="8000" :max-distance="120" />
    <VCard class="login-panel surface-border card-accent" max-width="420">
      <VAvatar color="primary" rounded="sm" size="42">
        <VIcon icon="mdi-book-open-page-variant-outline" />
      </VAvatar>
      <div>
        <h1 class="login-title">Documentation Hub</h1>
        <p class="muted-text">
          Sign in with SSO to manage, update, and review Confluence documentation.
        </p>
      </div>
      <VBtn block color="primary" prepend-icon="mdi-login" @click="auth.login">
        Continue with SSO
      </VBtn>
    </VCard>
  </div>
</template>

<style scoped>
.login-page {
  position: relative;
  display: grid;
  min-height: 100vh;
  place-items: center;
  padding: 24px;
  background-color: #f5f5f5;
}

.login-page > :not(canvas) {
  position: relative;
  z-index: 1;
}

.login-panel {
  display: grid;
  gap: 18px;
  padding: 24px;
}

.login-title {
  margin: 0 0 6px;
  font-size: 24px;
  line-height: 32px;
}
</style>

