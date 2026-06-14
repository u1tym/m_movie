<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { fetchVideo } from '../api/movie'
import { useVideoPlayer } from '../composables/useVideoPlayer'
import { formatMs } from '../config'
import type { VideoDetail } from '../types/movie'

const props = defineProps<{ id: string }>()
const route = useRoute()
const router = useRouter()

const VOLUME_KEY = 'm-movie-volume'
const MUTE_KEY = 'm-movie-muted'

const videoEl = ref<HTMLVideoElement | null>(null)
const detail = ref<VideoDetail | null>(null)
const pageError = ref<string | null>(null)
const seekValue = ref(0)
const volume = ref(Number(localStorage.getItem(VOLUME_KEY) ?? '1'))
const muted = ref(localStorage.getItem(MUTE_KEY) === 'true')
const volumeBeforeMute = ref(volume.value > 0 ? volume.value : 1)

const {
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
  cleanup,
} = useVideoPlayer(videoEl)

const videoId = computed(() => Number(props.id || route.params.id))
let detailLoadId = 0

const loadDetail = async (): Promise<void> => {
  const loadId = detailLoadId
  pageError.value = null
  try {
    detail.value = await fetchVideo(videoId.value)
    if (loadId !== detailLoadId) return
    if (detail.value.status !== 'ready') {
      pageError.value = 'この動画はまだ再生できません'
      return
    }
    await load(detail.value, true)
    if (loadId !== detailLoadId) return
    seekValue.value = detail.value.position_ms ?? 0
  } catch (e) {
    if (loadId !== detailLoadId) return
    pageError.value = e instanceof Error ? e.message : '動画の取得に失敗しました'
  }
}

onBeforeUnmount(() => {
  detailLoadId += 1
  cleanup()
})

onMounted(() => {
  void loadDetail()
})

watch(videoId, () => {
  void loadDetail()
})

const onTimeUpdate = (): void => {
  if (!videoEl.value) return
  seekValue.value = Math.round(videoEl.value.currentTime * 1000)
}

const onSeekInput = async (): Promise<void> => {
  await seekTo(seekValue.value)
}

const goNext = (): void => {
  if (nextVideo.value) {
    router.push(`/videos/${nextVideo.value.video_id}`)
  }
}

const goEdit = (): void => {
  router.push(`/videos/${videoId.value}/edit`)
}

const applyAudioSettings = (): void => {
  const el = videoEl.value
  if (!el) return
  el.volume = volume.value
  el.muted = muted.value
}

const onVolumeInput = (): void => {
  if (volume.value > 0) {
    volumeBeforeMute.value = volume.value
    muted.value = false
  }
  localStorage.setItem(VOLUME_KEY, String(volume.value))
  localStorage.setItem(MUTE_KEY, muted.value ? 'true' : 'false')
  applyAudioSettings()
}

const toggleMute = (): void => {
  if (muted.value) {
    muted.value = false
    if (volume.value === 0) {
      volume.value = volumeBeforeMute.value
    }
  } else {
    if (volume.value > 0) {
      volumeBeforeMute.value = volume.value
    }
    muted.value = true
  }
  localStorage.setItem(VOLUME_KEY, String(volume.value))
  localStorage.setItem(MUTE_KEY, muted.value ? 'true' : 'false')
  applyAudioSettings()
}

watch(videoEl, (el) => {
  if (el) {
    applyAudioSettings()
  }
})
</script>

<template>
  <div class="container player-page">
    <p v-if="pageError" class="error-banner">{{ pageError }}</p>
    <p v-if="error" class="error-banner">{{ error }}</p>

    <div v-if="detail" class="player-header">
      <h1>{{ detail.title }}</h1>
      <p v-if="detail.series_title" class="meta">{{ detail.series_title }}</p>
      <div class="genres">
        <span v-for="g in detail.genres" :key="g.genre_id" class="chip">{{ g.name }}</span>
      </div>
    </div>

    <div class="player-wrap card">
      <video
        ref="videoEl"
        class="video"
        playsinline
        @pause="onPause"
        @ended="onEnded"
        @timeupdate="onTimeUpdate"
        @waiting="onWaiting"
        @playing="onPlaying"
      />
      <p v-if="loading" class="loading">読み込み中...</p>
      <p v-else-if="buffering" class="loading">バッファリング中...</p>
    </div>

    <div v-if="playbackInfo" class="controls card">
      <div class="time">
        <span>{{ formatMs(seekValue) }}</span>
        <span>{{ formatMs(playbackInfo.duration_ms) }}</span>
      </div>
      <input
        v-model.number="seekValue"
        class="seek"
        type="range"
        min="0"
        :max="playbackInfo.duration_ms"
        step="1000"
        @change="onSeekInput"
      />
      <div class="buttons">
        <button class="btn btn-secondary" @click="togglePlay">再生 / 一時停止</button>
        <button v-if="nextVideo" class="btn" @click="goNext">次の動画</button>
        <button class="btn btn-ghost" @click="goEdit">編集</button>
      </div>
      <div class="volume-row">
        <button type="button" class="btn btn-ghost mute-btn" @click="toggleMute">
          {{ muted ? 'ミュート解除' : 'ミュート' }}
        </button>
        <input
          v-model.number="volume"
          class="volume"
          type="range"
          min="0"
          max="1"
          step="0.05"
          aria-label="音量"
          @input="onVolumeInput"
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
.player-page {
  max-width: 900px;
}

.player-header h1 {
  margin: 0 0 6px;
  font-size: 1.25rem;
}

.meta {
  margin: 0 0 8px;
  color: var(--muted);
  font-size: 0.875rem;
}

.genres {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 12px;
}

.player-wrap {
  padding: 0;
  overflow: hidden;
}

.video {
  width: 100%;
  display: block;
  background: #000;
  aspect-ratio: 16 / 9;
}

.loading {
  padding: 12px;
  text-align: center;
  color: var(--muted);
}

.controls {
  margin-top: 12px;
}

.time {
  display: flex;
  justify-content: space-between;
  font-size: 0.875rem;
  color: var(--muted);
  margin-bottom: 8px;
}

.seek {
  width: 100%;
  margin-bottom: 12px;
}

.buttons {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.volume-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 12px;
}

.mute-btn {
  flex-shrink: 0;
  min-width: 100px;
}

.volume {
  flex: 1;
  min-width: 0;
}
</style>
