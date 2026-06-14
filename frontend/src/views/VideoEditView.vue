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
  getVideoFileDurationMs,
  prepareVideoReplace,
  updateVideo,
  uploadThumbnail,
  uploadVideoFile,
} from '../api/movie'
import type { Genre, Series, VideoDetail } from '../types/movie'
import { useEditMode } from '../composables/useEditMode'
import {
  detectMp4VideoCodec,
  ffmpegH264Command,
  hevcUploadWarning,
  mp4VideoCodecLabel,
  type Mp4VideoCodec,
} from '../utils/mp4Codec'

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
const replacingVideo = ref(false)
const replaceProgress = ref('')
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
const replaceFile = ref<File | null>(null)
const replaceCodec = ref<Mp4VideoCodec | null>(null)
const replaceCodecWarning = ref<string | null>(null)

const videoId = (): number => Number(props.id || route.params.id)

const formatFileSize = (bytes: number): string => {
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

const formatDuration = (ms: number): string => {
  const totalSec = Math.floor(ms / 1000)
  const m = Math.floor(totalSec / 60)
  const s = totalSec % 60
  return `${m}:${String(s).padStart(2, '0')}`
}

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

const onReplaceFileChange = async (e: Event): Promise<void> => {
  const input = e.target as HTMLInputElement
  replaceFile.value = input.files?.[0] ?? null
  replaceCodec.value = null
  replaceCodecWarning.value = null

  if (!replaceFile.value) return

  try {
    const codec = await detectMp4VideoCodec(replaceFile.value)
    replaceCodec.value = codec
    if (codec === 'hevc') {
      replaceCodecWarning.value = hevcUploadWarning
    }
  } catch {
    replaceCodec.value = 'unknown'
  }
}

const replaceVideoFile = async (): Promise<void> => {
  if (!replaceFile.value) {
    error.value = '置き換える動画ファイルを選択してください'
    return
  }
  if (replaceCodec.value === 'hevc') {
    error.value = hevcUploadWarning
    return
  }
  if (
    !confirm(
      '現在の動画ファイルを削除し、選択したファイルに置き換えます。再生位置もリセットされます。よろしいですか？',
    )
  ) {
    return
  }

  replacingVideo.value = true
  error.value = null
  replaceProgress.value = '準備中...'

  try {
    const durationMs = await getVideoFileDurationMs(replaceFile.value)
    replaceProgress.value = '旧ファイルを削除中...'

    await prepareVideoReplace(videoId(), {
      duration_ms: durationMs,
      mime_type: replaceFile.value.type || 'video/mp4',
    })

    replaceProgress.value = 'アップロード中...'
    await uploadVideoFile(videoId(), replaceFile.value, durationMs, (u, t) => {
      replaceProgress.value = `アップロード中 ${u}/${t}`
    })

    replaceFile.value = null
    replaceCodec.value = null
    replaceCodecWarning.value = null
    replaceProgress.value = ''
    await load()
    router.push(editMode.value ? '/' : `/videos/${videoId()}`)
  } catch (e) {
    error.value = e instanceof Error ? e.message : '動画ファイルの置き換えに失敗しました'
    replaceProgress.value = ''
    await load()
  } finally {
    replacingVideo.value = false
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
    <p class="note">メタデータ・サムネイル・動画ファイルを変更できます。</p>
    <p v-if="error" class="error-banner">{{ error }}</p>
    <p v-if="replaceProgress" class="progress-text">{{ replaceProgress }}</p>
    <p v-if="loading">読み込み中...</p>

    <form v-else class="card form" @submit.prevent="save">
      <div class="field replace-field">
        <label>動画ファイル (MP4)</label>
        <p v-if="video" class="file-info">
          現在: {{ formatFileSize(video.file_size_bytes) }}
          ・ {{ formatDuration(video.duration_ms) }}
          ・ {{ video.status }}
        </p>
        <input
          type="file"
          accept="video/mp4,video/*"
          :disabled="replacingVideo || saving"
          @change="onReplaceFileChange"
        />
        <p v-if="replaceCodec" class="codec-info">
          選択ファイル: {{ mp4VideoCodecLabel(replaceCodec) }}
        </p>
        <p v-if="replaceCodecWarning" class="codec-warning">{{ replaceCodecWarning }}</p>
        <p v-if="replaceCodecWarning" class="codec-command">
          変換例: <code>{{ ffmpegH264Command() }}</code>
        </p>
        <button
          v-if="replaceFile"
          type="button"
          class="btn btn-secondary"
          :disabled="replacingVideo || saving || replaceCodec === 'hevc'"
          @click="replaceVideoFile"
        >
          {{ replacingVideo ? '置き換え中...' : '動画ファイルを置き換え' }}
        </button>
      </div>

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

.replace-field {
  padding-bottom: 16px;
  margin-bottom: 8px;
  border-bottom: 1px solid var(--border);
}

.file-info {
  margin: 0 0 8px;
  font-size: 0.8125rem;
  color: var(--muted);
}

.progress-text {
  color: var(--muted);
  margin-bottom: 12px;
}

.codec-info {
  margin: 6px 0 0;
  font-size: 0.875rem;
  color: var(--muted);
}

.codec-warning {
  margin: 8px 0 0;
  padding: 10px 12px;
  border-radius: 10px;
  background: rgba(239, 68, 68, 0.15);
  color: #fecaca;
  font-size: 0.875rem;
}

.codec-command {
  margin: 8px 0 0;
  font-size: 0.75rem;
  color: var(--muted);
  word-break: break-all;
}

.codec-command code {
  font-family: ui-monospace, monospace;
}
</style>
