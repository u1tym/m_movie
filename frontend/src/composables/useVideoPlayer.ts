import { ref, onUnmounted, type Ref } from 'vue'
import {
  fetchNextVideo,
  getVideoStreamUrl,
  savePlaybackState,
  startPlayback,
} from '../api/movie'
import type { NextVideoBrief, VideoDetail } from '../types/movie'

const waitForMediaEvent = (
  video: HTMLVideoElement,
  eventName: 'loadedmetadata' | 'canplay',
): Promise<void> =>
  new Promise((resolve, reject) => {
    const ready =
      eventName === 'loadedmetadata'
        ? video.readyState >= HTMLMediaElement.HAVE_METADATA
        : video.readyState >= HTMLMediaElement.HAVE_FUTURE_DATA
    if (ready) {
      resolve()
      return
    }
    const onEvent = (): void => {
      video.removeEventListener(eventName, onEvent)
      video.removeEventListener('error', onError)
      resolve()
    }
    const onError = (): void => {
      video.removeEventListener(eventName, onEvent)
      video.removeEventListener('error', onError)
      reject(new Error('動画の読み込みに失敗しました'))
    }
    video.addEventListener(eventName, onEvent)
    video.addEventListener('error', onError)
  })

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

      el.src = getVideoStreamUrl(detail.video_id)
      await waitForMediaEvent(el, 'loadedmetadata')

      if (start.position_ms > 0) {
        el.currentTime = start.position_ms / 1000
      }

      await waitForMediaEvent(el, 'canplay')

      await el.play().catch(() => {
        // 自動再生ブロックは許容
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
    el.currentTime = positionMs / 1000
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
