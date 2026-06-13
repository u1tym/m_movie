const trimSlash = (url: string): string => url.trim().replace(/\/$/, '')

/** デバッグモード（セッション延長をスキップ） */
export const isDebug = (): boolean => import.meta.env.VITE_DEBUG === 'true'

/** 動画 API の基点 */
export const getMovieApiBase = (): string => {
  if (import.meta.env.DEV) {
    return '/api/movie'
  }
  return trimSlash(import.meta.env.VITE_MOVIE_ORIGIN || '')
}

/** 認証 API の基点（POST /refresh） */
export const getLoginApiBase = (): string => {
  if (import.meta.env.DEV) {
    return '/api/auth'
  }
  return trimSlash(import.meta.env.VITE_LOGIN_ORIGIN || '')
}

export const formatMs = (ms: number): string => {
  const totalSec = Math.floor(ms / 1000)
  const h = Math.floor(totalSec / 3600)
  const m = Math.floor((totalSec % 3600) / 60)
  const s = totalSec % 60
  if (h > 0) {
    return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
  }
  return `${m}:${String(s).padStart(2, '0')}`
}
