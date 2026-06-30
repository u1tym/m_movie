import { ref, onBeforeUnmount, type Ref } from 'vue'
import {
  fetchNextPlaylistItem,
  fetchPrevPlaylistItem,
  savePlaylistPlaybackState,
  startPlaylistPlayback,
} from '../api/playlist'
import { getVideoStreamUrl } from '../api/movie'
import type { PlaylistPlaybackItem } from '../types/playlist'
import { hevcPlaybackError } from '../utils/mp4Codec'

const MEDIA_TIMEOUT_MS = 120_000

class LoadAbortedError extends Error {
  constructor() {
    super('aborted')
    this.name = 'LoadAbortedError'
  }
}

const videoErrorMessage = (video: HTMLVideoElement): string => {
  const code = video.error?.code
  if (code === MediaError.MEDIA_ERR_DECODE) {
    return '動画形式が再生できません（H.264 + AAC の MP4 を推奨）'
  }
  if (code === MediaError.MEDIA_ERR_SRC_NOT_SUPPORTED) {
    return hevcPlaybackError
  }
  return '動画の読み込みに失敗しました'
}

const waitForMediaEvent = (
  video: HTMLVideoElement,
  eventName: 'loadedmetadata' | 'canplay' | 'seeked',
  timeoutMs = MEDIA_TIMEOUT_MS,
  signal?: AbortSignal,
): Promise<void> =>
  new Promise((resolve, reject) => {
    if (signal?.aborted) {
      reject(new LoadAbortedError())
      return
    }
    let timeoutId: ReturnType<typeof setTimeout> | null = null
    const cleanup = (): void => {
      video.removeEventListener(eventName, onEvent)
      video.removeEventListener('error', onError)
      signal?.removeEventListener('abort', onAbort)
      if (timeoutId) clearTimeout(timeoutId)
    }
    const onEvent = (): void => { cleanup(); resolve() }
    const onError = (): void => { cleanup(); reject(new Error(videoErrorMessage(video))) }
    const onAbort = (): void => { cleanup(); reject(new LoadAbortedError()) }
    video.addEventListener(eventName, onEvent)
    video.addEventListener('error', onError)
    signal?.addEventListener('abort', onAbort)
    timeoutId = setTimeout(() => { cleanup(); reject(new Error('タイムアウト')) }, timeoutMs)
  })

export const usePlaylistPlayer = (videoRef: Ref<HTMLVideoElement | null>) => {
  const loading = ref(false)
  const error = ref<string | null>(null)
  const currentItem = ref<PlaylistPlaybackItem | null>(null)
  const playlistId = ref<number | null>(null)
  const buffering = ref(false)

  let saveTimer: ReturnType<typeof setInterval> | null = null
  let sessionId = 0
  let waitAbort: AbortController | null = null

  const cleanup = (): void => {
    sessionId += 1
    waitAbort?.abort()
    waitAbort = null
    if (saveTimer) {
      clearInterval(saveTimer)
      saveTimer = null
    }
    const el = videoRef.value
    if (el) {
      el.pause()
      el.removeAttribute('src')
      el.src = ''
      el.load()
    }
    currentItem.value = null
    buffering.value = false
  }

  const savePosition = async (): Promise<void> => {
    if (!playlistId.value || !currentItem.value || !videoRef.value) return
    const positionMs = Math.round(videoRef.value.currentTime * 1000)
    try {
      await savePlaylistPlaybackState(
        playlistId.value,
        currentItem.value.playlist_item_id,
        positionMs,
      )
    } catch {
      // ignore
    }
  }

  const seekVideo = async (
    video: HTMLVideoElement,
    positionMs: number,
    signal: AbortSignal,
    id: number,
  ): Promise<void> => {
    const targetSec = positionMs / 1000
    if (Math.abs(video.currentTime - targetSec) < 0.5) return
    const seekPromise = waitForMediaEvent(video, 'seeked', 30_000, signal)
    video.currentTime = targetSec
    try {
      await seekPromise
    } catch (e) {
      if (e instanceof LoadAbortedError || sessionId !== id) throw e
      await waitForMediaEvent(video, 'canplay', MEDIA_TIMEOUT_MS, signal)
    }
  }

  const loadItem = async (item: PlaylistPlaybackItem, fromStart: boolean): Promise<void> => {
    const id = sessionId
    loading.value = true
    error.value = null
    currentItem.value = item

    const controller = new AbortController()
    waitAbort = controller
    const { signal } = controller

    try {
      const el = videoRef.value
      if (!el) return

      const positionMs = fromStart ? 0 : item.position_ms
      el.src = getVideoStreamUrl(item.video_id, item.stream_token)
      await waitForMediaEvent(el, 'loadedmetadata', MEDIA_TIMEOUT_MS, signal)
      if (sessionId !== id) return
      await waitForMediaEvent(el, 'canplay', MEDIA_TIMEOUT_MS, signal)
      if (sessionId !== id) return

      if (positionMs > 0) {
        await seekVideo(el, positionMs, signal, id)
        if (sessionId !== id) return
        await waitForMediaEvent(el, 'canplay', MEDIA_TIMEOUT_MS, signal)
        if (sessionId !== id) return
      }

      await el.play().catch(() => {})
    } catch (e) {
      if (!(e instanceof LoadAbortedError) && sessionId === id) {
        error.value = e instanceof Error ? e.message : '再生に失敗しました'
      }
    } finally {
      if (sessionId === id) loading.value = false
    }
  }

  const start = async (id: number, resume = true): Promise<void> => {
    cleanup()
    playlistId.value = id
    sessionId += 1
    try {
      const item = await startPlaylistPlayback(id, resume)
      await loadItem(item, item.position_ms === 0)
      saveTimer = setInterval(() => { void savePosition() }, 10000)
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'プレイリスト再生の開始に失敗しました'
    }
  }

  const playNext = async (): Promise<void> => {
    if (!playlistId.value || !currentItem.value) return
    await savePosition()
    try {
      const next = await fetchNextPlaylistItem(
        playlistId.value,
        currentItem.value.playlist_item_id,
      )
      if (next.has_next && next.item) {
        await loadItem(next.item, true)
      }
    } catch (e) {
      error.value = e instanceof Error ? e.message : '次の動画の取得に失敗しました'
    }
  }

  const playPrev = async (): Promise<void> => {
    if (!playlistId.value || !currentItem.value) return
    await savePosition()
    try {
      const prev = await fetchPrevPlaylistItem(
        playlistId.value,
        currentItem.value.playlist_item_id,
      )
      if (prev.has_prev && prev.item) {
        await loadItem(prev.item, true)
      }
    } catch (e) {
      error.value = e instanceof Error ? e.message : '前の動画の取得に失敗しました'
    }
  }

  const onEnded = async (): Promise<void> => {
    await savePosition()
    if (!playlistId.value || !currentItem.value) return

    try {
      const next = await fetchNextPlaylistItem(
        playlistId.value,
        currentItem.value.playlist_item_id,
      )
      if (next.has_next && next.item) {
        await loadItem(next.item, true)
      } else {
        currentItem.value = { ...currentItem.value, has_next: false }
      }
    } catch (e) {
      error.value = e instanceof Error ? e.message : '次の動画の取得に失敗しました'
    }
  }

  const togglePlay = async (): Promise<void> => {
    const el = videoRef.value
    if (!el) return
    if (el.paused) {
      await el.play()
    } else {
      el.pause()
      await savePosition()
    }
  }

  const seekTo = async (positionMs: number): Promise<void> => {
    const el = videoRef.value
    if (!el) return
    const controller = new AbortController()
    try {
      await seekVideo(el, positionMs, controller.signal, sessionId)
    } catch (e) {
      if (e instanceof LoadAbortedError) return
      throw e
    }
    await savePosition()
  }

  const onWaiting = (): void => {
    buffering.value = true
  }

  const onPlaying = (): void => {
    buffering.value = false
  }

  onBeforeUnmount(() => {
    void savePosition()
    cleanup()
  })

  return {
    loading,
    error,
    currentItem,
    buffering,
    start,
    playNext,
    playPrev,
    onEnded,
    onPause: savePosition,
    togglePlay,
    seekTo,
    savePosition,
    onWaiting,
    onPlaying,
    cleanup,
  }
}
