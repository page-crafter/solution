import Keycloak from 'keycloak-js'
import { defineStore } from 'pinia'
import { computed, shallowRef } from 'vue'
import { setAuthTokenProvider, type AuthRefreshOptions } from '../api/client'
import { getRuntimeConfig } from '../config/runtime'

type KeycloakClient = InstanceType<typeof Keycloak>

const defaultDisplayName = 'Documentation editor'

export const useAuthStore = defineStore('auth', () => {
  const keycloak = shallowRef<KeycloakClient>()
  const initialized = shallowRef(false)
  const authenticated = shallowRef(false)
  const token = shallowRef<string>()
  const displayName = shallowRef(defaultDisplayName)

  const isReady = computed(() => initialized.value)
  const isAuthenticated = computed(() => authenticated.value)
  const roles = computed<string[]>(
    () => (keycloak.value?.tokenParsed as Record<string, unknown> | undefined)?.roles as string[] ?? [],
  )
  const isAdmin = computed(() => roles.value.includes('admin'))
  const isChat = computed(() => roles.value.includes('chat'))

  /** Creates the Keycloak SDK client after runtime config has been loaded. */
  function getKeycloak(): KeycloakClient {
    if (!keycloak.value) {
      const { url, realm, clientId } = getRuntimeConfig().auth.keycloak
      keycloak.value = new Keycloak({ url, realm, clientId })
    }
    return keycloak.value
  }

  /** Synchronizes Pinia state with the latest Keycloak SDK state. */
  function syncAuthState(): void {
    const client = keycloak.value
    authenticated.value = Boolean(client?.authenticated && client.token)
    token.value = client?.token
    displayName.value = authenticated.value
      ? String(
          client?.tokenParsed?.name
          || client?.tokenParsed?.preferred_username
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
    const client = getKeycloak()
    setAuthTokenProvider(() => token.value, refreshToken)
    client.onTokenExpired = () => {
      void refreshToken({ force: true }).catch(() => undefined)
    }
    client.onAuthLogout = clearAuthState
    client.onAuthRefreshSuccess = syncAuthState
    client.onAuthRefreshError = syncAuthState
    try {
      await client.init({
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
    return getKeycloak().login({ redirectUri: window.location.origin })
  }

  /** Logs the user out through the configured SSO provider. */
  function logout(): Promise<void> {
    return getKeycloak().logout({ redirectUri: window.location.origin })
  }

  /** Refreshes the access token when Keycloak reports it is close to expiry. */
  async function refreshToken(options: AuthRefreshOptions = {}): Promise<string | undefined> {
    const client = getKeycloak()
    if (!authenticated.value && !client.authenticated) {
      clearAuthState()
      return undefined
    }

    try {
      await client.updateToken(options.force ? -1 : 30)
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
