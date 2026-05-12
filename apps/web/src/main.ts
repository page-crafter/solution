import '@mdi/font/css/materialdesignicons.css'
import '@git-diff-view/vue/styles/diff-view.css'
import './assets/main.css'

import { createPinia } from 'pinia'
import { createApp } from 'vue'

import App from './App.vue'
import { router } from './router'
import { vuetify } from './plugins/vuetify'

/** Bootstraps the Vue application with routing, state, and Vuetify. */
function bootstrap(): void {
  const app = createApp(App)
  app.config.errorHandler = (err, _instance, info) => {
    console.error('[app error]', info, err)
  }
  app.use(createPinia())
  app.use(router)
  app.use(vuetify)
  app.mount('#app')
}

bootstrap()

