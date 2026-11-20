const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || '/api'
).replace(/\/+$/, '')

export class ApiError extends Error {
  constructor(message, status = 0, detail = null) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.detail = detail
  }
}

function getErrorMessage(detail, status) {
  if (typeof detail === 'string') {
    return detail
  }

  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        const field = (item.loc || [])
          .filter((part) => part !== 'body')
          .join('.')

        return field ? `${field}: ${item.msg}` : item.msg
      })
      .join('\n')
  }

  return `Request failed (${status}).`
}

export async function apiRequest(
  path,
  {
    method = 'GET',
    body,
    token,
    signal,
    timeoutMs = 15000,
  } = {},
) {
  if (!path.startsWith('/') || path.startsWith('//')) {
    throw new ApiError('API paths must start with a single slash.')
  }

  const controller = new AbortController()
  let timedOut = false

  const abortRequest = () => controller.abort()

  if (signal?.aborted) {
    controller.abort()
  } else {
    signal?.addEventListener('abort', abortRequest, { once: true })
  }

  const timeout = setTimeout(() => {
    timedOut = true
    controller.abort()
  }, timeoutMs)

  const headers = {
    Accept: 'application/json',
  }

  if (body !== undefined) {
    headers['Content-Type'] = 'application/json'
  }

  if (token) {
    headers.Authorization = `Bearer ${token}`
  }

  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: controller.signal,
      cache: 'no-store',
    })

    const text = await response.text()
    let data = null

    if (text) {
      try {
        data = JSON.parse(text)
      } catch {
        throw new ApiError(
          'The server returned an unexpected response.',
          response.status,
        )
      }
    }

    if (!response.ok) {
      throw new ApiError(
        getErrorMessage(data?.detail, response.status),
        response.status,
        data?.detail,
      )
    }

    return data
  } catch (error) {
    if (error instanceof ApiError) {
      throw error
    }

    if (timedOut) {
      throw new ApiError('The server took too long to respond. Please try again.')
    }

    if (controller.signal.aborted) {
      throw error
    }

    throw new ApiError(
      'Cannot connect to the backend. Check that it is running and the API address is correct.',
    )
  } finally {
    clearTimeout(timeout)
    signal?.removeEventListener('abort', abortRequest)
  }
}

export function checkBackendHealth(options = {}) {
  return apiRequest('/health', options)
}