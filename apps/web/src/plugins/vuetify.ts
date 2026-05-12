import { createVuetify } from 'vuetify'
import { aliases, mdi } from 'vuetify/iconsets/mdi'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import 'vuetify/styles'

export const vuetify = createVuetify({
  components,
  directives,
  icons: {
    defaultSet: 'mdi',
    aliases,
    sets: { mdi },
  },
  theme: {
    defaultTheme: 'confluenceLight',
    themes: {
      confluenceLight: {
        dark: false,
        colors: {
          background: '#f7f8fa',
          surface: '#ffffff',
          primary: '#0c66e4',
          secondary: '#44546f',
          success: '#1f845a',
          warning: '#f5a524',
          error: '#c9372c',
          info: '#0c66e4',
        },
      },
    },
  },
  defaults: {
    VBtn: { rounded: 'sm' },
    VCard: { rounded: 'lg', elevation: 0 },
    VTextField: { density: 'compact', variant: 'outlined' },
    VTextarea: { density: 'compact', variant: 'outlined' },
    VSelect: { density: 'compact', variant: 'outlined' },
    VDataTable: { density: 'compact' },
  },
})

