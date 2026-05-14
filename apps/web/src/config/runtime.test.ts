import { afterEach, describe, expect, it, vi } from 'vitest'
import { getRuntimeConfig, loadRuntimeConfig, resetRuntimeConfigForTests } from './runtime'

function jsonResponse(value: unknown, init: ResponseInit = {}): Response {
  return new Response(JSON.stringify(value), {
    headers: { 'Content-Type': 'application/json' },
    status: 200,
    ...init,
  })
}

describe('runtime config', () => {
  afterEach(() => {
    resetRuntimeConfigForTests()
    vi.unstubAllGlobals()
  })

  it('loads backend and auth settings from config.json', async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(jsonResponse({
      backend: {
        baseUrl: 'https://api.example.test/',
      },
      auth: {
        keycloak: {
          url: 'https://auth.example.test',
          realm: 'docs',
          clientId: 'docs-web',
        },
      },
    }))
    vi.stubGlobal('fetch', fetchMock)

    await loadRuntimeConfig()

    expect(fetchMock).toHaveBeenCalledWith('/config.json', { cache: 'no-store' })
    expect(getRuntimeConfig()).toEqual({
      backend: {
        baseUrl: 'https://api.example.test',
      },
      auth: {
        keycloak: {
          url: 'https://auth.example.test',
          realm: 'docs',
          clientId: 'docs-web',
        },
      },
      chat: {
        publicAccess: false,
      },
    })
  })

  it('keeps defaults when config.json is not served', async () => {
    vi.stubGlobal('fetch', vi.fn<typeof fetch>().mockResolvedValue(new Response(null, { status: 404 })))

    await loadRuntimeConfig()

    expect(getRuntimeConfig().backend.baseUrl).toBe('')
    expect(getRuntimeConfig().auth.keycloak.url).toBe('http://localhost:8080')
  })
})
