<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { fetchThumbnailBlob } from '../api/movie'
import { formatMs } from '../config'
import type { VideoSummary } from '../types/movie'

const props = defineProps<{ video: VideoSummary }>()
const router = useRouter()
const thumbUrl = ref<string | null>(null)

const loadThumb = async (): Promise<void> => {
  if (!props.video.has_thumbnail) return
  try {
    const blob = await fetchThumbnailBlob(props.video.video_id)
    thumbUrl.value = URL.createObjectURL(blob)
  } catch {
    thumbUrl.value = null
  }
}

watch(
  () => props.video.video_id,
  () => {
    if (thumbUrl.value) URL.revokeObjectURL(thumbUrl.value)
    thumbUrl.value = null
    void loadThumb()
  },
  { immediate: true },
)

onMounted(() => {
  void loadThumb()
})

onUnmounted(() => {
  if (thumbUrl.value) URL.revokeObjectURL(thumbUrl.value)
})

const open = (): void => {
  if (props.video.status === 'ready') {
    router.push(`/videos/${props.video.video_id}`)
  }
}
</script>

<template>
  <article class="card video-card" @click="open">
    <div class="thumb">
      <img v-if="thumbUrl" :src="thumbUrl" :alt="video.title" />
      <div v-else class="thumb-placeholder">No Image</div>
      <span v-if="video.status !== 'ready'" class="status-badge">{{ video.status }}</span>
      <span class="duration">{{ formatMs(video.duration_ms) }}</span>
    </div>
    <div class="body">
      <h3>{{ video.title }}</h3>
      <p v-if="video.series_title" class="meta">{{ video.series_title }}</p>
      <p v-if="video.episode_number" class="meta">第{{ video.episode_number }}話</p>
      <div class="genres">
        <span v-for="g in video.genres" :key="g.genre_id" class="chip">{{ g.name }}</span>
      </div>
      <p v-if="video.position_ms" class="progress">続きから {{ formatMs(video.position_ms) }}</p>
    </div>
  </article>
</template>

<style scoped>
.video-card {
  cursor: pointer;
  overflow: hidden;
  padding: 0;
}

.thumb {
  position: relative;
  aspect-ratio: 16 / 9;
  background: var(--surface-2);
}

.thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.thumb-placeholder {
  height: 100%;
  display: grid;
  place-items: center;
  color: var(--muted);
  font-size: 0.875rem;
}

.duration,
.status-badge {
  position: absolute;
  bottom: 8px;
  padding: 2px 8px;
  border-radius: 6px;
  background: rgba(0, 0, 0, 0.7);
  font-size: 0.75rem;
}

.duration {
  right: 8px;
}

.status-badge {
  left: 8px;
  background: rgba(239, 68, 68, 0.8);
}

.body {
  padding: 12px;
}

.body h3 {
  margin: 0 0 6px;
  font-size: 1rem;
}

.meta,
.progress {
  margin: 0 0 4px;
  font-size: 0.8125rem;
  color: var(--muted);
}

.genres {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
}
</style>
