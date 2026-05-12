const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

export interface AuthRefreshOptions {
  force?: boolean
}

type AuthTokenProvider = () => string | undefined
type AuthTokenRefresher = (options?: AuthRefreshOptions) => Promise<string | undefined>

let tokenProvider: AuthTokenProvider | undefined
let tokenRefresher: AuthTokenRefresher | undefined
let refreshPromise: Promise<string | undefined> | undefined

/** Registers the current auth token provider for API requests. */
export function setAuthTokenProvider(
  provider: AuthTokenProvider,
  refresher?: AuthTokenRefresher,
): void {
  tokenProvider = provider
  tokenRefresher = refresher
  refreshPromise = undefined
}

/** Refreshes the auth token while sharing one in-flight refresh across requests. */
async function refreshAuthToken(force = false): Promise<string | undefined> {
  if (!tokenRefresher) {
    return tokenProvider?.()
  }

  if (force && refreshPromise) {
    await refreshPromise.catch(() => undefined)
  }

  if (!refreshPromise) {
    refreshPromise = tokenRefresher({ force }).finally(() => {
      refreshPromise = undefined
    })
  }

  return refreshPromise
}

/** Creates headers for one request attempt with the newest available token. */
function buildHeaders(init: RequestInit, token: string | undefined): Headers {
  const headers = new Headers(init.headers)
  if (!headers.has('Accept')) {
    headers.set('Accept', 'application/json')
  }
  if (!(typeof FormData !== 'undefined' && init.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }
  if (token) {
    headers.set('Authorization', `Bearer ${token}`)
  } else {
    headers.delete('Authorization')
  }
  return headers
}

/** Sends one fetch attempt without parsing the response body. */
function sendRequest(path: string, init: RequestInit, token: string | undefined): Promise<Response> {
  return fetch(`${API_BASE_URL}${path}`, { ...init, headers: buildHeaders(init, token) })
}

/** Sends an authenticated request and returns the raw response. */
export async function apiRawRequest(path: string, init: RequestInit = {}): Promise<Response> {
  const token = await refreshAuthToken().catch(() => tokenProvider?.())
  let response = await sendRequest(path, init, token)

  if (response.status === 401 && tokenRefresher) {
    const refreshedToken = await refreshAuthToken(true).catch(() => undefined)
    if (refreshedToken) {
      response = await sendRequest(path, init, refreshedToken)
    }
  }

  return response
}

/** Sends an authenticated JSON request to the FastAPI backend. */
export async function apiRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await apiRawRequest(path, init)

  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || `Request failed with ${response.status}`)
  }
  if (response.status === 204) {
    return undefined as T
  }
  return response.json() as Promise<T>
}

/** Builds a JSON request body without repeating headers in feature clients. */
export function jsonBody(value: unknown): RequestInit {
  return { body: JSON.stringify(value) }
}
