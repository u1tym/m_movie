import { refreshAccessToken } from '../auth'
import { getMovieApiBase, isDebug } from '../config'

interface ApiErrorBody {
  error?: {
    code?: string
    message?: string
    details?: Array<{ field?: string; message?: string }>
  }
  detail?: string
}

const parseError = async (response: Response): Promise<string> => {
  let message = `HTTP ${response.status}`
  try {
    const data = (await response.json()) as ApiErrorBody
    if (data.error?.message) {
      message = data.error.message
    } else if (data.detail) {
      message = typeof data.detail === 'string' ? data.detail : message
    }
  } catch {
    // ignore
  }
  return message
}

export const toQuery = (
  params: Record<string, string | number | boolean | undefined>,
): string => {
  const query = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== '' && value !== false) {
      query.set(key, String(value))
    }
  })
  const qs = query.toString()
  return qs ? `?${qs}` : ''
}

const ensureSession = async (): Promise<void> => {
  if (!isDebug()) {
    await refreshAccessToken()
  }
}

export const movieRequest = async <T>(
  path: string,
  init?: RequestInit,
  query?: Record<string, string | number | boolean | undefined>,
): Promise<T> => {
  await ensureSession()

  const qs = query ? toQuery(query) : ''
  const url = `${getMovieApiBase()}${path}${qs}`
  const isFormData = init?.body instanceof FormData

  const response = await fetch(url, {
    credentials: 'include',
    ...init,
    headers: isFormData
      ? { ...(init?.headers || {}) }
      : {
          Accept: 'application/json',
          'Content-Type': 'application/json',
          ...(init?.headers || {}),
        },
  })

  if (!response.ok) {
    throw new Error(await parseError(response))
  }

  if (response.status === 204) {
    return undefined as T
  }

  return (await response.json()) as T
}

export const movieFetchBlob = async (path: string): Promise<Blob> => {
  await ensureSession()

  const response = await fetch(`${getMovieApiBase()}${path}`, {
    credentials: 'include',
  })

  if (!response.ok) {
    throw new Error(await parseError(response))
  }

  return response.blob()
}
