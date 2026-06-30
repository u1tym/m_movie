<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { fetchVideos } from '../api/movie'
import {
  deletePlaylist,
  fetchPlaylist,
  updatePlaylist,
  updatePlaylistItems,
} from '../api/playlist'
import { formatMs } from '../config'
import type { PlaylistDetail } from '../types/playlist'
import type { VideoSummary } from '../types/movie'

const props = defineProps<{ id: string }>()
const route = useRoute()
const router = useRouter()

const playlistId = computed(() => Number(props.id || route.params.id))
const playlist = ref<PlaylistDetail | null>(null)
const allVideos = ref<VideoSummary[]>([])
const selectedVideoIds = ref<number[]>([])
const name = ref('')
const description = ref('')
const loading = ref(false)
const saving = ref(false)
const error = ref<string | null>(null)

const load = async (): Promise<void> => {
  loading.value = true
  error.value = null
  try {
    const [p, videos] = await Promise.all([
      fetchPlaylist(playlistId.value),
      fetchVideos({ page: 1, per_page: 100, status: 'ready' }),
    ])
    playlist.value = p
    name.value = p.name
    description.value = p.description ?? ''
    selectedVideoIds.value = p.items.map((i) => i.video_id)
    allVideos.value = videos.items
  } catch (e) {
    error.value = e instanceof Error ? e.message : '取得に失敗しました'
  } finally {
    loading.value = false
  }
}

onMounted(() => { void load() })

const addVideo = (videoId: number): void => {
  selectedVideoIds.value = [...selectedVideoIds.value, videoId]
}

const removeAt = (index: number): void => {
  selectedVideoIds.value = selectedVideoIds.value.filter((_, i) => i !== index)
}

const moveUp = (index: number): void => {
  if (index <= 0) return
  const ids = [...selectedVideoIds.value]
  ;[ids[index - 1], ids[index]] = [ids[index], ids[index - 1]]
  selectedVideoIds.value = ids
}

const moveDown = (index: number): void => {
  const ids = [...selectedVideoIds.value]
  if (index >= ids.length - 1) return
  ;[ids[index], ids[index + 1]] = [ids[index + 1], ids[index]]
  selectedVideoIds.value = ids
}

const videoTitle = (videoId: number): string =>
  allVideos.value.find((v) => v.video_id === videoId)?.title ?? `動画 #${videoId}`

const save = async (): Promise<void> => {
  saving.value = true
  error.value = null
  try {
    await updatePlaylist(playlistId.value, {
      name: name.value.trim(),
      description: description.value || null,
    })
    await updatePlaylistItems(playlistId.value, selectedVideoIds.value)
    router.push('/playlists')
  } catch (e) {
    error.value = e instanceof Error ? e.message : '保存に失敗しました'
  } finally {
    saving.value = false
  }
}

const remove = async (): Promise<void> => {
  if (!confirm('このプレイリストを削除しますか？')) return
  try {
    await deletePlaylist(playlistId.value)
    router.push('/playlists')
  } catch (e) {
    error.value = e instanceof Error ? e.message : '削除に失敗しました'
  }
}
</script>

<template>
  <div class="container">
    <h1>プレイリスト編集</h1>
    <p v-if="error" class="error-banner">{{ error }}</p>
    <p v-if="loading">読み込み中...</p>

    <form v-else class="form" @submit.prevent="save">
      <div class="card">
        <div class="field">
          <label>名前</label>
          <input v-model="name" required maxlength="500" />
        </div>
        <div class="field">
          <label>説明</label>
          <textarea v-model="description" />
        </div>
      </div>

      <section class="card section">
        <h2>再生リスト（上から順）</h2>
        <p v-if="selectedVideoIds.length === 0" class="muted">動画を追加してください</p>
        <ul v-else class="selected-list">
          <li v-for="(vid, index) in selectedVideoIds" :key="`${index}-${vid}`">
            <span>{{ index + 1 }}. {{ videoTitle(vid) }}</span>
            <div class="row-actions">
              <button type="button" class="btn btn-ghost" @click="moveUp(index)">↑</button>
              <button type="button" class="btn btn-ghost" @click="moveDown(index)">↓</button>
              <button type="button" class="btn btn-ghost" @click="removeAt(index)">削除</button>
            </div>
          </li>
        </ul>
      </section>

      <section class="card section">
        <h2>動画を追加</h2>
        <ul class="video-pick-list">
          <li v-for="v in allVideos" :key="v.video_id">
            <span>{{ v.title }} ({{ formatMs(v.duration_ms) }})</span>
            <button type="button" class="btn btn-secondary" @click="addVideo(v.video_id)">
              追加
            </button>
          </li>
        </ul>
      </section>

      <div class="actions">
        <button class="btn" type="submit" :disabled="saving">
          {{ saving ? '保存中...' : '保存' }}
        </button>
        <button type="button" class="btn btn-danger" @click="remove">削除</button>
        <RouterLink to="/playlists" class="btn btn-ghost">戻る</RouterLink>
      </div>
    </form>
  </div>
</template>

<style scoped>
h1 {
  margin: 0 0 16px;
}

.section {
  margin-top: 14px;
}

.section h2 {
  margin: 0 0 12px;
  font-size: 1rem;
}

.muted {
  color: var(--muted);
}

.selected-list,
.video-pick-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: grid;
  gap: 8px;
}

.selected-list li,
.video-pick-list li {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  flex-wrap: wrap;
}

.row-actions {
  display: flex;
  gap: 4px;
}

.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 16px;
}
</style>
