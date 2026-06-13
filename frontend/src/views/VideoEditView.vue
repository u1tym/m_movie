<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  createGenre,
  deleteVideo,
  fetchGenres,
  fetchSeries,
  fetchVideo,
  updateVideo,
} from '../api/movie'
import type { Genre, Series, VideoDetail } from '../types/movie'

const props = defineProps<{ id: string }>()
const route = useRoute()
const router = useRouter()

const video = ref<VideoDetail | null>(null)
const genres = ref<Genre[]>([])
const seriesList = ref<Series[]>([])
const loading = ref(false)
const saving = ref(false)
const error = ref<string | null>(null)

const title = ref('')
const description = ref('')
const seriesId = ref<number | null>(null)
const episodeNumber = ref<number | null>(null)
const episodeTitle = ref('')
const sortOrder = ref(0)
const selectedGenreIds = ref<number[]>([])
const newGenreName = ref('')

const videoId = (): number => Number(props.id || route.params.id)

const load = async (): Promise<void> => {
  loading.value = true
  error.value = null
  try {
    const [v, g, s] = await Promise.all([
      fetchVideo(videoId()),
      fetchGenres(),
      fetchSeries(1, 100),
    ])
    video.value = v
    genres.value = g.items
    seriesList.value = s.items

    title.value = v.title
    description.value = v.description ?? ''
    seriesId.value = v.series_id
    episodeNumber.value = v.episode_number
    episodeTitle.value = v.episode_title ?? ''
    sortOrder.value = v.sort_order
    selectedGenreIds.value = v.genres.map((x) => x.genre_id)
  } catch (e) {
    error.value = e instanceof Error ? e.message : '取得に失敗しました'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  void load()
})

const toggleGenre = (id: number): void => {
  if (selectedGenreIds.value.includes(id)) {
    selectedGenreIds.value = selectedGenreIds.value.filter((x) => x !== id)
  } else {
    selectedGenreIds.value = [...selectedGenreIds.value, id]
  }
}

const addGenre = async (): Promise<void> => {
  if (!newGenreName.value.trim()) return
  try {
    const created = await createGenre({ name: newGenreName.value.trim() })
    genres.value = [...genres.value, created]
    selectedGenreIds.value = [...selectedGenreIds.value, created.genre_id]
    newGenreName.value = ''
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'ジャンル追加に失敗しました'
  }
}

const save = async (): Promise<void> => {
  saving.value = true
  error.value = null
  try {
    await updateVideo(videoId(), {
      title: title.value.trim(),
      description: description.value || null,
      series_id: seriesId.value,
      episode_number: episodeNumber.value,
      episode_title: episodeTitle.value || null,
      sort_order: sortOrder.value,
      genre_ids: selectedGenreIds.value,
    })
    router.push(`/videos/${videoId()}`)
  } catch (e) {
    error.value = e instanceof Error ? e.message : '更新に失敗しました'
  } finally {
    saving.value = false
  }
}

const remove = async (): Promise<void> => {
  if (!confirm('この動画を削除しますか？')) return
  try {
    await deleteVideo(videoId())
    router.push('/')
  } catch (e) {
    error.value = e instanceof Error ? e.message : '削除に失敗しました'
  }
}
</script>

<template>
  <div class="container">
    <h1>動画編集</h1>
    <p class="note">動画ファイルの入れ替えはできません。メタデータのみ変更できます。</p>
    <p v-if="error" class="error-banner">{{ error }}</p>
    <p v-if="loading">読み込み中...</p>

    <form v-else class="card form" @submit.prevent="save">
      <div class="field">
        <label>タイトル</label>
        <input v-model="title" required maxlength="500" />
      </div>
      <div class="field">
        <label>説明</label>
        <textarea v-model="description" />
      </div>
      <div class="field">
        <label>作品</label>
        <select v-model="seriesId">
          <option :value="null">なし</option>
          <option v-for="s in seriesList" :key="s.series_id" :value="s.series_id">
            {{ s.title }}
          </option>
        </select>
      </div>
      <div class="field-row">
        <div class="field">
          <label>話数</label>
          <input v-model.number="episodeNumber" type="number" min="1" />
        </div>
        <div class="field">
          <label>話タイトル</label>
          <input v-model="episodeTitle" maxlength="500" />
        </div>
        <div class="field">
          <label>並び順</label>
          <input v-model.number="sortOrder" type="number" min="0" />
        </div>
      </div>
      <div class="field">
        <label>ジャンル</label>
        <div class="genre-filter">
          <button
            v-for="g in genres"
            :key="g.genre_id"
            type="button"
            class="chip"
            :class="{ 'chip-active': selectedGenreIds.includes(g.genre_id) }"
            @click="toggleGenre(g.genre_id)"
          >
            {{ g.name }}
          </button>
        </div>
        <div class="add-genre">
          <input v-model="newGenreName" placeholder="新しいジャンル名" maxlength="100" />
          <button type="button" class="btn btn-secondary" @click="addGenre">追加</button>
        </div>
      </div>
      <div class="actions">
        <button class="btn" type="submit" :disabled="saving">{{ saving ? '保存中...' : '保存' }}</button>
        <button type="button" class="btn btn-danger" @click="remove">削除</button>
      </div>
    </form>
  </div>
</template>

<style scoped>
h1 {
  margin: 0 0 8px;
}

.note {
  color: var(--muted);
  font-size: 0.875rem;
  margin-bottom: 16px;
}

.form {
  display: flex;
  flex-direction: column;
}

.field-row {
  display: grid;
  gap: 10px;
}

@media (min-width: 640px) {
  .field-row {
    grid-template-columns: repeat(3, 1fr);
  }
}

.genre-filter {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 8px;
}

.genre-filter button {
  border: none;
}

.add-genre {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 8px;
}

.add-genre input {
  min-height: 44px;
  padding: 10px 12px;
  border: 1px solid var(--border);
  border-radius: 10px;
  background: var(--surface);
  color: var(--text);
}

.actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}
</style>
