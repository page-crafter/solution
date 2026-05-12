<script setup lang="ts">
import { computed, shallowRef } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import ChatWidget from '../components/common/ChatWidget.vue'
import ParticleBackground from '../components/common/ParticleBackground.vue'

const route = useRoute()
const auth = useAuthStore()
const drawer = shallowRef(true)

const hasRole = computed(() => auth.isAdmin || auth.isChat)

const allItems = [
  { title: 'Dashboard', icon: 'mdi-view-dashboard-outline', to: '/dashboard' },
  { title: 'Pages', icon: 'mdi-file-document-multiple-outline', to: '/pages' },
  { title: 'Chat', icon: 'mdi-message-text-outline', to: '/chat' },
  { title: 'Runs', icon: 'mdi-timeline-clock-outline', to: '/runs' },
]

const items = computed(() => auth.isAdmin ? allItems : [])
const activeTitle = computed(() => allItems.find((item) => item.to === route.path)?.title ?? 'Documentation Hub')
</script>

<template>
  <!-- No role: minimal centered layout -->
  <template v-if="!hasRole">
    <VAppBar height="48" flat border="b">
      <div class="editor-bar__brand">
        <VAvatar size="28" rounded="sm" color="primary">
          <VIcon icon="mdi-book-open-page-variant-outline" size="16" />
        </VAvatar>
        <span class="editor-bar__name">Documentation Hub</span>
      </div>
      <VSpacer />
      <VBtn prepend-icon="mdi-logout" variant="text" size="small" @click="auth.logout">
        Sign out
      </VBtn>
    </VAppBar>
    <VMain>
      <div class="no-role-center">
        <ParticleBackground particle-color="#b0b8c4" :speed="0.4" :density="8000" :max-distance="120" />
        <VCard class="no-role-card surface-border card-accent" max-width="420">
          <VAvatar color="primary" rounded="sm" size="42">
            <VIcon icon="mdi-book-open-page-variant-outline" />
          </VAvatar>
          <div>
            <h1 class="no-role-title">Documentation Hub</h1>
            <p class="muted-text">
              Your account does not have the required permissions. Contact your administrator.
            </p>
          </div>
        </VCard>
      </div>
    </VMain>
  </template>

  <!-- Admin or Chat: full layout -->
  <template v-else>
    <VNavigationDrawer v-if="auth.isAdmin" v-model="drawer" width="272" color="surface" border="end">
      <template #prepend>
        <div class="drawer-header">
          <VAvatar size="32" rounded="sm" color="primary">
            <VIcon icon="mdi-book-open-page-variant-outline" />
          </VAvatar>
          <div>
            <div class="product-name">Documentation Hub</div>
            <div class="muted-text text-caption">Confluence updater</div>
          </div>
        </div>
      </template>

      <VList nav density="compact">
        <VListItem
          v-for="item in items"
          :key="item.to"
          :to="item.to"
          :prepend-icon="item.icon"
          :title="item.title"
          rounded="sm"
        />
      </VList>

      <template #append>
        <div class="drawer-footer">
          <div class="text-caption muted-text">Signed in as</div>
          <div class="text-body-2 user-name">{{ auth.displayName }}</div>
        </div>
      </template>
    </VNavigationDrawer>

    <VAppBar height="48" flat border="b" class="workspace-band">
      <VBtn v-if="auth.isAdmin" icon="mdi-menu" variant="text" size="small" @click="drawer = !drawer" />
      <VToolbarTitle class="text-subtitle-1">{{ activeTitle }}</VToolbarTitle>
      <VSpacer />
      <VBtn v-if="auth.isAdmin" prepend-icon="mdi-file-edit-outline" variant="text" size="small" to="/editor">
        Editor
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
</template>

<style scoped>
.no-role-center {
  position: relative;
  display: grid;
  min-height: calc(100dvh - 48px);
  place-items: center;
  padding: 24px;
  background-color: #f5f5f5;
}

.no-role-center > :not(canvas) {
  position: relative;
  z-index: 1;
}

.no-role-card {
  display: grid;
  gap: 18px;
  padding: 24px;
}

.no-role-title {
  margin: 0 0 6px;
  font-size: 24px;
  line-height: 32px;
}

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

.drawer-header {
  display: flex;
  gap: 12px;
  align-items: center;
  padding: 14px 16px;
  border-bottom: 1px solid #dfe1e6;
}

.product-name {
  font-weight: 700;
  line-height: 18px;
}

.drawer-footer {
  padding: 12px 16px;
  border-top: 1px solid #dfe1e6;
}

.user-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
