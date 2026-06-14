<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  createGenre,
  deleteVideo,
  fetchGenres,
  fetchSeries,
  fetchThumbnailBlob,
  fetchVideo,
  updateVideo,
  uploadThumbnail,
} from '../api/movie'
import type { Genre, Series, VideoDetail } from '../types/movie'
import { useEditMode } from '../composables/useEditMode'

const props = defineProps<{ id: string }>()
const route = useRoute()
const router = useRouter()
const { editMode } = useEditMode()

const video = ref<VideoDetail | null>(null)
const genres = ref<Genre[]>([])
const seriesList = ref<Series[]>([])
const loading = ref(false)
const saving = ref(false)
const uploadingThumb = ref(false)
const error = ref<string | null>(null)

const title = ref('')
const description = ref('')
const seriesId = ref<number | null>(null)
const episodeNumber = ref<number | null>(null)
const episodeTitle = ref('')
const sortOrder = ref(0)
const selectedGenreIds = ref<number[]>([])
const newGenreName = ref('')
const currentThumbUrl = ref<string | null>(null)
const pendingThumbUrl = ref<string | null>(null)
const thumbFile = ref<File | null>(null)

const videoId = (): number => Number(props.id || route.params.id)

const revokeThumbUrls = (): void => {
  if (currentThumbUrl.value) {
    URL.revokeObjectURL(currentThumbUrl.value)
    currentThumbUrl.value = null
  }
  if (pendingThumbUrl.value) {
    URL.revokeObjectURL(pendingThumbUrl.value)
    pendingThumbUrl.value = null
  }
}

const loadCurrentThumb = async (hasThumbnail: boolean): Promise<void> => {
  if (currentThumbUrl.value) {
    URL.revokeObjectURL(currentThumbUrl.value)
    currentThumbUrl.value = null
  }
  if (!hasThumbnail) return
  try {
    const blob = await fetchThumbnailBlob(videoId())
    currentThumbUrl.value = URL.createObjectURL(blob)
  } catch {
    currentThumbUrl.value = null
  }
}

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

    await loadCurrentThumb(v.has_thumbnail)
  } catch (e) {
    error.value = e instanceof Error ? e.message : '取得に失敗しました'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  void load()
})

onUnmounted(() => {
  revokeThumbUrls()
})

const onThumbChange = (e: Event): void => {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0] ?? null
  if (pendingThumbUrl.value) {
    URL.revokeObjectURL(pendingThumbUrl.value)
    pendingThumbUrl.value = null
  }
  thumbFile.value = file
  if (file) {
    pendingThumbUrl.value = URL.createObjectURL(file)
  }
}

const uploadPendingThumbnail = async (): Promise<void> => {
  if (!thumbFile.value) return
  uploadingThumb.value = true
  error.value = null
  try {
    await uploadThumbnail(
      videoId(),
      thumbFile.value,
      thumbFile.value.type || 'image/jpeg',
    )
    if (video.value) {
      video.value.has_thumbnail = true
    }
    await loadCurrentThumb(true)
    if (pendingThumbUrl.value) {
      URL.revokeObjectURL(pendingThumbUrl.value)
      pendingThumbUrl.value = null
    }
    thumbFile.value = null
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'サムネイルの更新に失敗しました'
    throw e
  } finally {
    uploadingThumb.value = false
  }
}

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
    if (thumbFile.value) {
      await uploadPendingThumbnail()
    }
    await updateVideo(videoId(), {
      title: title.value.trim(),
      description: description.value || null,
      series_id: seriesId.value,
      episode_number: episodeNumber.value,
      episode_title: episodeTitle.value || null,
      sort_order: sortOrder.value,
      genre_ids: selectedGenreIds.value,
    })
    router.push(editMode.value ? '/' : `/videos/${videoId()}`)
  } catch (e) {
    if (!error.value) {
      error.value = e instanceof Error ? e.message : '更新に失敗しました'
    }
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
    <p class="note">動画ファイルの入れ替えはできません。メタデータとサムネイルは変更できます。</p>
    <p v-if="error" class="error-banner">{{ error }}</p>
    <p v-if="loading">読み込み中...</p>

    <form v-else class="card form" @submit.prevent="save">
      <div class="field thumb-field">
        <label>サムネイル画像</label>
        <div class="thumb-preview">
          <img
            v-if="pendingThumbUrl || currentThumbUrl"
            :src="pendingThumbUrl || currentThumbUrl || undefined"
            alt="サムネイル"
          />
          <div v-else class="thumb-placeholder">サムネイルなし</div>
        </div>
        <input type="file" accept="image/*" @change="onThumbChange" />
        <p v-if="pendingThumbUrl" class="thumb-note">新しい画像が選択されています（保存時に反映）</p>
        <button
          v-if="thumbFile"
          type="button"
          class="btn btn-secondary"
          :disabled="uploadingThumb || saving"
          @click="uploadPendingThumbnail"
        >
          {{ uploadingThumb ? '更新中...' : 'サムネイルだけ更新' }}
        </button>
      </div>

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

.thumb-field {
  margin-bottom: 8px;
}

.thumb-preview {
  aspect-ratio: 16 / 9;
  max-width: 320px;
  margin-bottom: 10px;
  border-radius: 10px;
  overflow: hidden;
  background: var(--surface-2);
}

.thumb-preview img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.thumb-placeholder {
  height: 100%;
  min-height: 120px;
  display: grid;
  place-items: center;
  color: var(--muted);
  font-size: 0.875rem;
}

.thumb-note {
  margin: 8px 0 0;
  font-size: 0.8125rem;
  color: var(--muted);
}
</style>
