import { getLoginApiBase } from './config'

/** POST /refresh — 有効な JWT Cookie を延長 */
export const refreshAccessToken = async (): Promise<void> => {
  const response = await fetch(`${getLoginApiBase()}/refresh`, {
    method: 'POST',
    credentials: 'include',
    headers: { Accept: 'application/json' },
  })

  if (response.ok) {
    return
  }

  let message = `HTTP ${response.status}: セッション更新に失敗しました`
  try {
    const data = (await response.json()) as { detail?: string }
    if (data.detail) {
      message = data.detail
    }
  } catch {
    // ignore
  }
  throw new Error(message)
}
