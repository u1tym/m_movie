import { ref, onUnmounted, type Ref } from 'vue'
import {
  fetchNextVideo,
  getVideoStreamUrl,
  savePlaybackState,
  startPlayback,
} from '../api/movie'
import type { NextVideoBrief, VideoDetail } from '../types/movie'
import { hevcPlaybackError } from '../utils/mp4Codec'

const MEDIA_TIMEOUT_MS = 120_000

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
): Promise<void> =>
  new Promise((resolve, reject) => {
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

    const cleanup = (): void => {
      video.removeEventListener(eventName, onEvent)
      video.removeEventListener('error', onError)
      if (timeoutId !== null) {
        clearTimeout(timeoutId)
      }
    }

    const onEvent = (): void => {
      cleanup()
      resolve()
    }
    const onError = (): void => {
      cleanup()
      reject(new Error(videoErrorMessage(video)))
    }

    video.addEventListener(eventName, onEvent)
    video.addEventListener('error', onError)
    timeoutId = setTimeout(() => {
      cleanup()
      reject(new Error('動画の読み込みがタイムアウトしました'))
    }, timeoutMs)
  })

const seekVideo = async (video: HTMLVideoElement, positionMs: number): Promise<void> => {
  const targetSec = positionMs / 1000
  if (Math.abs(video.currentTime - targetSec) < 0.5) {
    return
  }
  const seekPromise = waitForMediaEvent(video, 'seeked', 30_000)
  video.currentTime = targetSec
  try {
    await seekPromise
  } catch {
    // iOS 等で seeked が発火しない場合
    await waitForMediaEvent(video, 'canplay', 30_000)
  }
}

export const useVideoPlayer = (videoRef: Ref<HTMLVideoElement | null>) => {
  const loading = ref(false)
  const error = ref<string | null>(null)
  const playbackInfo = ref<{ position_ms: number; duration_ms: number } | null>(null)
  const nextVideo = ref<NextVideoBrief | null>(null)
  const buffering = ref(false)

  let saveTimer: ReturnType<typeof setInterval> | null = null
  let currentVideoId: number | null = null

  const cleanup = (): void => {
    if (saveTimer) {
      clearInterval(saveTimer)
      saveTimer = null
    }
    if (videoRef.value) {
      videoRef.value.pause()
      videoRef.value.removeAttribute('src')
      videoRef.value.load()
    }
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

  const load = async (detail: VideoDetail, resume = true): Promise<void> => {
    cleanup()
    loading.value = true
    error.value = null
    buffering.value = false
    currentVideoId = detail.video_id

    try {
      const start = await startPlayback(detail.video_id, resume)
      playbackInfo.value = {
        position_ms: start.position_ms,
        duration_ms: start.duration_ms,
      }

      const el = videoRef.value
      if (!el) return

      // video 要素は fetch と違い Cookie を送れないことがあるため、
      // playback/start で発行した stream_token を URL に付与する
      el.src = getVideoStreamUrl(detail.video_id, start.stream_token)
      await waitForMediaEvent(el, 'loadedmetadata')
      await waitForMediaEvent(el, 'canplay')

      if (start.position_ms > 0) {
        await seekVideo(el, start.position_ms)
        await waitForMediaEvent(el, 'canplay')
      }

      await el.play().catch(() => {
        // 自動再生ブロックは許容（ユーザーが再生ボタンを押せる）
      })

      const next = await fetchNextVideo(detail.video_id)
      nextVideo.value = next.has_next ? next.video : null

      saveTimer = setInterval(() => {
        void savePosition()
      }, 10000)
    } catch (e) {
      error.value = e instanceof Error ? e.message : '再生の準備に失敗しました'
    } finally {
      loading.value = false
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
    await seekVideo(el, positionMs)
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

  onUnmounted(cleanup)

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
