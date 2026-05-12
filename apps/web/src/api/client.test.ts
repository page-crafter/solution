import { afterEach, describe, expect, it, vi } from 'vitest'
import { apiRequest, setAuthTokenProvider, type AuthRefreshOptions } from './client'

function jsonResponse(value: unknown, init: ResponseInit = {}): Response {
  return new Response(JSON.stringify(value), {
    headers: { 'Content-Type': 'application/json' },
    status: 200,
    ...init,
  })
}

describe('apiRequest', () => {
  afterEach(() => {
    setAuthTokenProvider(() => undefined)
    vi.unstubAllGlobals()
  })

  it('refreshes the access token before sending a request', async () => {
    let token = 'expired-token'
    const refreshToken = vi.fn(async () => {
      token = 'fresh-token'
      return token
    })
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(jsonResponse({ ok: true }))
    vi.stubGlobal('fetch', fetchMock)

    setAuthTokenProvider(() => token, refreshToken)

    await expect(apiRequest('/api/kpis')).resolves.toEqual({ ok: true })

    expect(refreshToken).toHaveBeenCalledWith({ force: false })
    const request = fetchMock.mock.calls[0]?.[1] as RequestInit
    expect(new Headers(request.headers).get('Authorization')).toBe('Bearer fresh-token')
  })

  it('forces a refresh and retries once after a 401 response', async () => {
    let token = 'stale-token'
    const refreshToken = vi.fn(async (options?: AuthRefreshOptions) => {
      if (options?.force) {
        token = 'fresh-token'
      }
      return token
    })
    const fetchMock = vi.fn<typeof fetch>()
      .mockResolvedValueOnce(jsonResponse({ detail: 'Invalid authentication token' }, { status: 401 }))
      .mockResolvedValueOnce(jsonResponse({ ok: true }))
    vi.stubGlobal('fetch', fetchMock)

    setAuthTokenProvider(() => token, refreshToken)

    await expect(apiRequest('/api/kpis')).resolves.toEqual({ ok: true })

    expect(fetchMock).toHaveBeenCalledTimes(2)
    expect(refreshToken).toHaveBeenNthCalledWith(1, { force: false })
    expect(refreshToken).toHaveBeenNthCalledWith(2, { force: true })

    const firstRequest = fetchMock.mock.calls[0]?.[1] as RequestInit
    const secondRequest = fetchMock.mock.calls[1]?.[1] as RequestInit
    expect(new Headers(firstRequest.headers).get('Authorization')).toBe('Bearer stale-token')
    expect(new Headers(secondRequest.headers).get('Authorization')).toBe('Bearer fresh-token')
  })
})
