export interface RuntimeConfig {
  backend: {
    baseUrl: string
  }
  auth: {
    keycloak: {
      url: string
      realm: string
      clientId: string
    }
  }
}

const DEFAULT_RUNTIME_CONFIG: RuntimeConfig = {
  backend: {
    baseUrl: import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000',
  },
  auth: {
    keycloak: {
      url: import.meta.env.VITE_KEYCLOAK_URL ?? 'http://localhost:8080',
      realm: import.meta.env.VITE_KEYCLOAK_REALM ?? 'page-crafter',
      clientId: import.meta.env.VITE_KEYCLOAK_CLIENT_ID ?? 'page-crafter-web',
    },
  },
}

let runtimeConfig: RuntimeConfig = DEFAULT_RUNTIME_CONFIG

function asRecord(value: unknown): Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
    ? value as Record<string, unknown>
    : {}
}

function readString(value: unknown, fallback: string, allowEmpty = false): string {
  if (typeof value !== 'string') {
    return fallback
  }
  if (!allowEmpty && !value.trim()) {
    return fallback
  }
  return value
}

function normalizeBaseUrl(baseUrl: string): string {
  return baseUrl.replace(/\/+$/, '')
}

function normalizeRuntimeConfig(raw: unknown): RuntimeConfig {
  const root = asRecord(raw)
  const backend = asRecord(root.backend)
  const auth = asRecord(root.auth)
  const keycloak = asRecord(auth.keycloak)

  return {
    backend: {
      baseUrl: normalizeBaseUrl(readString(
        backend.baseUrl,
        DEFAULT_RUNTIME_CONFIG.backend.baseUrl,
        true,
      )),
    },
    auth: {
      keycloak: {
        url: readString(keycloak.url, DEFAULT_RUNTIME_CONFIG.auth.keycloak.url),
        realm: readString(keycloak.realm, DEFAULT_RUNTIME_CONFIG.auth.keycloak.realm),
        clientId: readString(keycloak.clientId, DEFAULT_RUNTIME_CONFIG.auth.keycloak.clientId),
      },
    },
  }
}

function configUrl(): string {
  return `${import.meta.env.BASE_URL}config.json`
}

/** Loads browser-facing runtime configuration before the app starts. */
export async function loadRuntimeConfig(): Promise<RuntimeConfig> {
  const response = await fetch(configUrl(), { cache: 'no-store' })

  if (response.status === 404) {
    runtimeConfig = DEFAULT_RUNTIME_CONFIG
    return runtimeConfig
  }

  if (!response.ok) {
    throw new Error(`Unable to load frontend config (${response.status})`)
  }

  runtimeConfig = normalizeRuntimeConfig(await response.json())
  return runtimeConfig
}

/** Returns the active runtime configuration. */
export function getRuntimeConfig(): RuntimeConfig {
  return runtimeConfig
}

export function resetRuntimeConfigForTests(): void {
  runtimeConfig = DEFAULT_RUNTIME_CONFIG
}
