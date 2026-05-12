import Keycloak from 'keycloak-js'
import { defineStore } from 'pinia'
import { computed, shallowRef } from 'vue'
import { setAuthTokenProvider, type AuthRefreshOptions } from '../api/client'

const keycloak = new Keycloak({
  url: import.meta.env.VITE_KEYCLOAK_URL ?? 'http://localhost:8080',
  realm: import.meta.env.VITE_KEYCLOAK_REALM ?? 'page-crafter',
  clientId: import.meta.env.VITE_KEYCLOAK_CLIENT_ID ?? 'page-crafter-web',
})

const defaultDisplayName = 'Documentation editor'

export const useAuthStore = defineStore('auth', () => {
  const initialized = shallowRef(false)
  const authenticated = shallowRef(false)
  const token = shallowRef<string>()
  const displayName = shallowRef(defaultDisplayName)

  const isReady = computed(() => initialized.value)
  const isAuthenticated = computed(() => authenticated.value)
  const roles = computed<string[]>(
    () => (keycloak.tokenParsed as Record<string, unknown>)?.roles as string[] ?? [],
  )
  const isAdmin = computed(() => roles.value.includes('admin'))
  const isChat = computed(() => roles.value.includes('chat'))

  /** Synchronizes Pinia state with the latest Keycloak SDK state. */
  function syncAuthState(): void {
    authenticated.value = Boolean(keycloak.authenticated && keycloak.token)
    token.value = keycloak.token
    displayName.value = authenticated.value
      ? String(
          keycloak.tokenParsed?.name
          || keycloak.tokenParsed?.preferred_username
          || defaultDisplayName,
        )
      : defaultDisplayName
  }

  /** Clears local auth state after Keycloak reports an expired session. */
  function clearAuthState(): void {
    authenticated.value = false
    token.value = undefined
    displayName.value = defaultDisplayName
  }

  /** Initializes Keycloak PKCE and registers the API token provider. */
  async function initialize(): Promise<void> {
    if (initialized.value) {
      return
    }
    setAuthTokenProvider(() => token.value, refreshToken)
    keycloak.onTokenExpired = () => {
      void refreshToken({ force: true }).catch(() => undefined)
    }
    keycloak.onAuthLogout = clearAuthState
    keycloak.onAuthRefreshSuccess = syncAuthState
    keycloak.onAuthRefreshError = syncAuthState
    try {
      await keycloak.init({
        onLoad: 'check-sso',
        pkceMethod: 'S256',
        silentCheckSsoRedirectUri: `${window.location.origin}/silent-check-sso.html`,
      })
      syncAuthState()
    } finally {
      initialized.value = true
    }
  }

  /** Redirects the user to the configured SSO provider. */
  function login(): Promise<void> {
    return keycloak.login({ redirectUri: window.location.origin })
  }

  /** Logs the user out through the configured SSO provider. */
  function logout(): Promise<void> {
    return keycloak.logout({ redirectUri: window.location.origin })
  }

  /** Refreshes the access token when Keycloak reports it is close to expiry. */
  async function refreshToken(options: AuthRefreshOptions = {}): Promise<string | undefined> {
    if (!authenticated.value && !keycloak.authenticated) {
      clearAuthState()
      return undefined
    }

    try {
      await keycloak.updateToken(options.force ? -1 : 30)
      syncAuthState()
      return token.value
    } catch (error) {
      syncAuthState()
      throw error
    }
  }

  return {
    displayName,
    initialize,
    isAdmin,
    isAuthenticated,
    isChat,
    isReady,
    login,
    logout,
    refreshToken,
    roles,
    token,
  }
})
