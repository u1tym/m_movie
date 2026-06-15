<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  createGenre,
  createSeries,
  createVideo,
  fetchGenres,
  fetchSeries,
  getVideoFileDurationMs,
  uploadThumbnail,
  uploadVideoFile,
} from '../api/movie'
import type { Genre, Series } from '../types/movie'
import {
  detectMp4VideoCodec,
  ffmpegH264Command,
  hevcUploadWarning,
  mp4VideoCodecLabel,
  type Mp4VideoCodec,
} from '../utils/mp4Codec'
import { generateDefaultThumbnail } from '../utils/videoThumbnail'

const router = useRouter()

const title = ref('')
const description = ref('')
const episodeNumber = ref<number | undefined>(undefined)
const episodeTitle = ref('')
const sortOrder = ref(0)
const selectedGenreIds = ref<number[]>([])
const seriesId = ref<number | undefined>(undefined)
const newSeriesTitle = ref('')
const file = ref<File | null>(null)
const thumbFile = ref<File | null>(null)

const genres = ref<Genre[]>([])
const seriesList = ref<Series[]>([])
const loading = ref(false)
const error = ref<string | null>(null)
const progress = ref('')
const newGenreName = ref('')
const detectedCodec = ref<Mp4VideoCodec | null>(null)
const codecWarning = ref<string | null>(null)

const loadMasters = async (): Promise<void> => {
  const [g, s] = await Promise.all([fetchGenres(), fetchSeries(1, 100)])
  genres.value = g.items
  seriesList.value = s.items
}

onMounted(() => {
  void loadMasters()
})

const onFileChange = async (e: Event): Promise<void> => {
  const input = e.target as HTMLInputElement
  file.value = input.files?.[0] ?? null
  detectedCodec.value = null
  codecWarning.value = null

  if (!file.value) return

  try {
    const codec = await detectMp4VideoCodec(file.value)
    detectedCodec.value = codec
    if (codec === 'hevc') {
      codecWarning.value = hevcUploadWarning
    }
  } catch {
    detectedCodec.value = 'unknown'
  }
}

const onThumbChange = (e: Event): void => {
  const input = e.target as HTMLInputElement
  thumbFile.value = input.files?.[0] ?? null
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

const submit = async (): Promise<void> => {
  if (!title.value.trim() || !file.value) {
    error.value = 'タイトルと動画ファイルは必須です'
    return
  }

  if (detectedCodec.value === 'hevc') {
    error.value = hevcUploadWarning
    return
  }

  loading.value = true
  error.value = null
  progress.value = '準備中...'

  try {
    let targetSeriesId = seriesId.value
    if (newSeriesTitle.value.trim()) {
      const series = await createSeries({ title: newSeriesTitle.value.trim() })
      targetSeriesId = series.series_id
    }

    const durationMs = await getVideoFileDurationMs(file.value)
    progress.value = 'メタデータ登録中...'

    const created = await createVideo({
      title: title.value.trim(),
      description: description.value || null,
      series_id: targetSeriesId ?? null,
      episode_number: episodeNumber.value ?? null,
      episode_title: episodeTitle.value || null,
      sort_order: sortOrder.value,
      duration_ms: durationMs,
      mime_type: file.value.type || 'video/mp4',
      genre_ids: selectedGenreIds.value,
    })

    await uploadVideoFile(created.video_id, file.value, durationMs, (u, t) => {
      progress.value = `アップロード中 ${u}/${t}`
    })

    if (thumbFile.value) {
      progress.value = 'サムネイル登録中...'
      await uploadThumbnail(created.video_id, thumbFile.value, thumbFile.value.type || 'image/jpeg')
    } else {
      progress.value = 'サムネイル生成中...'
      const thumb = await generateDefaultThumbnail(file.value, durationMs)
      await uploadThumbnail(created.video_id, thumb, 'image/jpeg')
    }

    router.push('/')
  } catch (e) {
    error.value = e instanceof Error ? e.message : '登録に失敗しました'
  } finally {
    loading.value = false
    progress.value = ''
  }
}
</script>

<template>
  <div class="container">
    <h1>動画登録</h1>
    <p v-if="error" class="error-banner">{{ error }}</p>
    <p v-if="progress" class="progress-text">{{ progress }}</p>

    <form class="card form" @submit.prevent="submit">
      <div class="field">
        <label>タイトル *</label>
        <input v-model="title" required maxlength="500" />
      </div>

      <div class="field">
        <label>説明</label>
        <textarea v-model="description" />
      </div>

      <div class="field">
        <label>動画ファイル (MP4) *</label>
        <input type="file" accept="video/mp4,video/*" required @change="onFileChange" />
        <p v-if="detectedCodec" class="codec-info">
          検出コーデック: {{ mp4VideoCodecLabel(detectedCodec) }}
        </p>
        <p v-if="codecWarning" class="codec-warning">{{ codecWarning }}</p>
        <p v-if="codecWarning" class="codec-command">
          変換例: <code>{{ ffmpegH264Command() }}</code>
        </p>
        <p class="codec-hint">iPhone 対応: H.264 (libx264) + AAC、`-movflags +faststart` 推奨</p>
      </div>

      <div class="field">
        <label>サムネイル画像</label>
        <input type="file" accept="image/*" @change="onThumbChange" />
        <p class="thumb-hint">未指定の場合、5秒地点（5秒未満の動画は先頭フレーム）を自動でサムネイルにします</p>
      </div>

      <div class="field">
        <label>作品（既存）</label>
        <select v-model="seriesId">
          <option :value="undefined">なし（単発）</option>
          <option v-for="s in seriesList" :key="s.series_id" :value="s.series_id">
            {{ s.title }}
          </option>
        </select>
      </div>

      <div class="field">
        <label>新規作品タイトル（入力時は新規作成）</label>
        <input v-model="newSeriesTitle" maxlength="500" />
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

      <button class="btn" type="submit" :disabled="loading || detectedCodec === 'hevc'">
        {{ loading ? '登録中...' : '登録する' }}
      </button>
    </form>
  </div>
</template>

<style scoped>
h1 {
  margin: 0 0 16px;
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

.codec-hint {
  margin: 8px 0 0;
  font-size: 0.75rem;
  color: var(--muted);
}

.thumb-hint {
  margin: 6px 0 0;
  font-size: 0.75rem;
  color: var(--muted);
}
</style>
