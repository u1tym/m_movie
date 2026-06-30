<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { fetchPlaylist } from '../api/playlist'
import { usePlaylistPlayer } from '../composables/usePlaylistPlayer'
import { formatMs } from '../config'
import type { PlaylistDetail } from '../types/playlist'

const props = defineProps<{ id: string }>()
const route = useRoute()
const videoEl = ref<HTMLVideoElement | null>(null)
const playlist = ref<PlaylistDetail | null>(null)
const pageError = ref<string | null>(null)
const seekValue = ref(0)

const playlistId = computed(() => Number(props.id || route.params.id))

const {
  loading,
  error,
  currentItem,
  buffering,
  start,
  playNext,
  playPrev,
  onEnded,
  onPause,
  togglePlay,
  seekTo,
  onWaiting,
  onPlaying,
  cleanup,
} = usePlaylistPlayer(videoEl)

let mountId = 0

onMounted(async () => {
  const id = ++mountId
  try {
    playlist.value = await fetchPlaylist(playlistId.value)
    if (mountId !== id) return
    if (playlist.value.items.length === 0) {
      pageError.value = 'プレイリストに動画がありません'
      return
    }
    await start(playlistId.value, true)
    if (mountId !== id) return
    seekValue.value = currentItem.value?.position_ms ?? 0
  } catch (e) {
    if (mountId !== id) return
    pageError.value = e instanceof Error ? e.message : '読み込みに失敗しました'
  }
})

onBeforeUnmount(() => {
  mountId += 1
  cleanup()
})

const onTimeUpdate = (): void => {
  if (!videoEl.value) return
  seekValue.value = Math.round(videoEl.value.currentTime * 1000)
}

const onSeekInput = async (): Promise<void> => {
  await seekTo(seekValue.value)
}

const handleEnded = (): void => {
  void onEnded()
}

const handlePause = (): void => {
  void onPause()
}
</script>

<template>
  <div class="container player-page">
    <h1>{{ playlist?.name ?? 'プレイリスト再生' }}</h1>
    <p v-if="pageError" class="error-banner">{{ pageError }}</p>
    <p v-if="error" class="error-banner">{{ error }}</p>

    <div class="player-wrap card">
      <video
        ref="videoEl"
        class="video"
        playsinline
        @pause="handlePause"
        @ended="handleEnded"
        @timeupdate="onTimeUpdate"
        @waiting="onWaiting"
        @playing="onPlaying"
      />
      <p v-if="loading" class="loading">読み込み中...</p>
      <p v-if="buffering" class="loading">バッファリング...</p>
    </div>

    <div v-if="currentItem" class="controls card">
      <p class="now-playing">{{ currentItem.title }}</p>
      <p class="save-hint">再生位置は一時停止時・10秒ごとに自動保存されます</p>
      <div class="time">
        <span>{{ formatMs(seekValue) }}</span>
        <span>{{ formatMs(currentItem.duration_ms) }}</span>
      </div>
      <input
        v-model.number="seekValue"
        class="seek"
        type="range"
        min="0"
        :max="currentItem.duration_ms"
        step="1000"
        @change="onSeekInput"
      />
      <div class="buttons">
        <button
          class="btn btn-secondary"
          :disabled="!currentItem.has_prev"
          @click="playPrev"
        >
          前の話
        </button>
        <button class="btn btn-secondary" @click="togglePlay">再生 / 一時停止</button>
        <button
          class="btn btn-secondary"
          :disabled="!currentItem.has_next"
          @click="playNext"
        >
          次の話
        </button>
        <RouterLink to="/playlists" class="btn btn-ghost">一覧へ</RouterLink>
      </div>
    </div>
  </div>
</template>

<style scoped>
.player-page {
  max-width: 900px;
}

h1 {
  margin: 0 0 12px;
  font-size: 1.25rem;
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

.now-playing {
  margin: 0 0 4px;
  font-weight: 600;
}

.save-hint {
  margin: 0 0 12px;
  font-size: 0.75rem;
  color: var(--muted);
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

.buttons .btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
</style>
