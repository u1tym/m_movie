<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { fetchGenres, fetchVideos } from '../api/movie'
import VideoCard from '../components/VideoCard.vue'
import type { Genre, VideoSummary } from '../types/movie'

const videos = ref<VideoSummary[]>([])
const genres = ref<Genre[]>([])
const loading = ref(false)
const error = ref<string | null>(null)
const page = ref(1)
const totalPages = ref(1)
const selectedGenreId = ref<number | undefined>(undefined)
const searchQuery = ref('')
const statusFilter = ref<string | undefined>(undefined)

const load = async (): Promise<void> => {
  loading.value = true
  error.value = null
  try {
    const result = await fetchVideos({
      page: page.value,
      per_page: 20,
      genre_id: selectedGenreId.value,
      status: statusFilter.value,
      q: searchQuery.value || undefined,
      sort: 'created_at',
      order: 'desc',
    })
    videos.value = result.items
    totalPages.value = result.pagination.total_pages
  } catch (e) {
    error.value = e instanceof Error ? e.message : '一覧の取得に失敗しました'
  } finally {
    loading.value = false
  }
}

const loadGenres = async (): Promise<void> => {
  try {
    const result = await fetchGenres()
    genres.value = result.items
  } catch {
    genres.value = []
  }
}

const applyFilter = (): void => {
  page.value = 1
  void load()
}

watch([page], () => {
  void load()
})

onMounted(() => {
  void loadGenres()
  void load()
})
</script>

<template>
  <div class="container">
    <div class="toolbar">
      <h1>動画一覧</h1>
      <div class="filters">
        <input
          v-model="searchQuery"
          type="search"
          placeholder="タイトル検索"
          @keyup.enter="applyFilter"
        />
        <select v-model="statusFilter" @change="applyFilter">
          <option :value="undefined">再生可能のみ</option>
          <option value="all">すべて</option>
          <option value="uploading">アップロード中</option>
          <option value="error">エラー</option>
        </select>
      </div>
      <div class="genre-filter">
        <button
          class="chip"
          :class="{ 'chip-active': selectedGenreId === undefined }"
          @click="selectedGenreId = undefined; applyFilter()"
        >
          すべて
        </button>
        <button
          v-for="g in genres"
          :key="g.genre_id"
          class="chip"
          :class="{ 'chip-active': selectedGenreId === g.genre_id }"
          @click="selectedGenreId = g.genre_id; applyFilter()"
        >
          {{ g.name }}
        </button>
      </div>
    </div>

    <p v-if="error" class="error-banner">{{ error }}</p>
    <p v-if="loading">読み込み中...</p>

    <div v-else-if="videos.length === 0" class="empty card">
      動画がありません。「登録」から追加してください。
    </div>

    <div v-else class="grid">
      <VideoCard v-for="v in videos" :key="v.video_id" :video="v" />
    </div>

    <div v-if="totalPages > 1" class="pager">
      <button class="btn btn-secondary" :disabled="page <= 1" @click="page -= 1">前へ</button>
      <span>{{ page }} / {{ totalPages }}</span>
      <button class="btn btn-secondary" :disabled="page >= totalPages" @click="page += 1">次へ</button>
    </div>
  </div>
</template>

<style scoped>
.toolbar h1 {
  margin: 0 0 12px;
  font-size: 1.5rem;
}

.filters {
  display: grid;
  gap: 8px;
  margin-bottom: 12px;
}

.filters input,
.filters select {
  min-height: 44px;
  padding: 10px 12px;
  border: 1px solid var(--border);
  border-radius: 10px;
  background: var(--surface);
  color: var(--text);
}

.genre-filter {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 16px;
}

.genre-filter button {
  border: none;
}

.grid {
  display: grid;
  gap: 14px;
}

@media (min-width: 640px) {
  .grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (min-width: 960px) {
  .grid {
    grid-template-columns: repeat(3, 1fr);
  }

  .filters {
    grid-template-columns: 1fr 200px;
  }
}

.empty {
  text-align: center;
  color: var(--muted);
}

.pager {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  margin-top: 20px;
}
</style>
