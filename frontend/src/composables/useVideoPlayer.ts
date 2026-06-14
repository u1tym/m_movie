import { ref, onBeforeUnmount, type Ref } from 'vue'
import {
  fetchNextVideo,
  getVideoStreamUrl,
  savePlaybackState,
  startPlayback,
} from '../api/movie'
import type { NextVideoBrief, VideoDetail } from '../types/movie'
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
  if (code === MediaError.MEDIA_ERR_NETWORK) {
    return '動画の取得に失敗しました（ネットワークまたは認証）'
  }
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

    const ready =
      eventName === 'loadedmetadata'
        ? video.readyState >= HTMLMediaElement.HAVE_METADATA
        : eventName === 'canplay'
          ? video.readyState >= HTMLMediaElement.HAVE_FUTURE_DATA
          : false
    if (ready) {
      resolve()
      return
    }

    let timeoutId: ReturnType<typeof setTimeout> | null = null

    const removeListeners = (): void => {
      video.removeEventListener(eventName, onEvent)
      video.removeEventListener('error', onError)
      signal?.removeEventListener('abort', onAbort)
      if (timeoutId !== null) {
        clearTimeout(timeoutId)
      }
    }

    const onEvent = (): void => {
      removeListeners()
      resolve()
    }
    const onError = (): void => {
      removeListeners()
      reject(new Error(videoErrorMessage(video)))
    }
    const onAbort = (): void => {
      removeListeners()
      reject(new LoadAbortedError())
    }

    video.addEventListener(eventName, onEvent)
    video.addEventListener('error', onError)
    signal?.addEventListener('abort', onAbort)
    timeoutId = setTimeout(() => {
      removeListeners()
      reject(new Error('動画の読み込みがタイムアウトしました'))
    }, timeoutMs)
  })

const stopVideoElement = (video: HTMLVideoElement): void => {
  video.pause()
  video.removeAttribute('src')
  video.src = ''
  video.load()
}

export const useVideoPlayer = (videoRef: Ref<HTMLVideoElement | null>) => {
  const loading = ref(false)
  const error = ref<string | null>(null)
  const playbackInfo = ref<{ position_ms: number; duration_ms: number } | null>(null)
  const nextVideo = ref<NextVideoBrief | null>(null)
  const buffering = ref(false)

  let saveTimer: ReturnType<typeof setInterval> | null = null
  let currentVideoId: number | null = null
  let activeVideo: HTMLVideoElement | null = null
  let sessionId = 0
  let waitAbort: AbortController | null = null

  const isActiveSession = (id: number): boolean => id === sessionId

  const cleanup = (): void => {
    sessionId += 1
    waitAbort?.abort()
    waitAbort = null

    if (saveTimer) {
      clearInterval(saveTimer)
      saveTimer = null
    }

    const el = activeVideo ?? videoRef.value
    if (el) {
      stopVideoElement(el)
    }
    activeVideo = null
    currentVideoId = null
    buffering.value = false
  }

  const savePosition = async (completed = false): Promise<void> => {
    if (!currentVideoId || !videoRef.value) return
    const positionMs = Math.round(videoRef.value.currentTime * 1000)
    try {
      await savePlaybackState(currentVideoId, positionMs, completed)
    } catch {
      // 保存失敗は再生を止めない
    }
  }

  const seekVideo = async (
    video: HTMLVideoElement,
    positionMs: number,
    signal: AbortSignal,
    id: number,
  ): Promise<void> => {
    const targetSec = positionMs / 1000
    if (Math.abs(video.currentTime - targetSec) < 0.5) {
      return
    }
    const seekPromise = waitForMediaEvent(video, 'seeked', 30_000, signal)
    video.currentTime = targetSec
    try {
      await seekPromise
    } catch (e) {
      if (e instanceof LoadAbortedError || !isActiveSession(id)) {
        throw e
      }
      await waitForMediaEvent(video, 'canplay', 30_000, signal)
    }
  }

  const load = async (detail: VideoDetail, resume = true): Promise<void> => {
    cleanup()
    const id = sessionId
    loading.value = true
    error.value = null

    const controller = new AbortController()
    waitAbort = controller
    const { signal } = controller

    try {
      const start = await startPlayback(detail.video_id, resume)
      if (!isActiveSession(id)) return

      playbackInfo.value = {
        position_ms: start.position_ms,
        duration_ms: start.duration_ms,
      }

      const el = videoRef.value
      if (!el) return

      activeVideo = el
      currentVideoId = detail.video_id

      el.src = getVideoStreamUrl(detail.video_id, start.stream_token)
      await waitForMediaEvent(el, 'loadedmetadata', MEDIA_TIMEOUT_MS, signal)
      if (!isActiveSession(id)) return

      await waitForMediaEvent(el, 'canplay', MEDIA_TIMEOUT_MS, signal)
      if (!isActiveSession(id)) return

      if (start.position_ms > 0) {
        await seekVideo(el, start.position_ms, signal, id)
        if (!isActiveSession(id)) return
        await waitForMediaEvent(el, 'canplay', MEDIA_TIMEOUT_MS, signal)
        if (!isActiveSession(id)) return
      }

      await el.play().catch(() => {
        // 自動再生ブロックは許容
      })
      if (!isActiveSession(id)) {
        stopVideoElement(el)
        return
      }

      const next = await fetchNextVideo(detail.video_id)
      if (!isActiveSession(id)) return
      nextVideo.value = next.has_next ? next.video : null

      saveTimer = setInterval(() => {
        void savePosition()
      }, 10000)
    } catch (e) {
      if (e instanceof LoadAbortedError || !isActiveSession(id)) {
        return
      }
      error.value = e instanceof Error ? e.message : '再生の準備に失敗しました'
    } finally {
      if (isActiveSession(id)) {
        loading.value = false
      }
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

  const onPause = (): void => {
    void savePosition()
  }

  const onEnded = (): void => {
    void savePosition(true)
  }

  const onWaiting = (): void => {
    buffering.value = true
  }

  const onPlaying = (): void => {
    buffering.value = false
  }

  onBeforeUnmount(cleanup)

  return {
    loading,
    error,
    playbackInfo,
    nextVideo,
    buffering,
    load,
    togglePlay,
    seekTo,
    onPause,
    onEnded,
    onWaiting,
    onPlaying,
    savePosition,
    cleanup,
  }
}
