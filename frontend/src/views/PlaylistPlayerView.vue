<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
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
  onEnded,
  onPause,
  togglePlay,
  savePosition,
} = usePlaylistPlayer(videoEl)

onMounted(async () => {
  try {
    playlist.value = await fetchPlaylist(playlistId.value)
    if (playlist.value.items.length === 0) {
      pageError.value = 'プレイリストに動画がありません'
      return
    }
    await start(playlistId.value, true)
    seekValue.value = currentItem.value?.position_ms ?? 0
  } catch (e) {
    pageError.value = e instanceof Error ? e.message : '読み込みに失敗しました'
  }
})

const onTimeUpdate = (): void => {
  if (!videoEl.value) return
  seekValue.value = Math.round(videoEl.value.currentTime * 1000)
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
      />
      <p v-if="loading" class="loading">読み込み中...</p>
      <p v-if="buffering" class="loading">バッファリング...</p>
    </div>

    <div v-if="currentItem" class="controls card">
      <p class="now-playing">
        {{ currentItem.title }}
        <span v-if="currentItem.has_next" class="chip">次あり</span>
      </p>
      <div class="time">
        <span>{{ formatMs(seekValue) }}</span>
        <span>{{ formatMs(currentItem.duration_ms) }}</span>
      </div>
      <div class="buttons">
        <button class="btn btn-secondary" @click="togglePlay">再生 / 一時停止</button>
        <button class="btn btn-ghost" @click="savePosition">位置を保存</button>
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
  margin: 0 0 8px;
  font-weight: 600;
}

.time {
  display: flex;
  justify-content: space-between;
  font-size: 0.875rem;
  color: var(--muted);
  margin-bottom: 12px;
}

.buttons {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
</style>
