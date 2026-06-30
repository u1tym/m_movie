<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { createPlaylist, fetchPlaylists } from '../api/playlist'
import type { PlaylistSummary } from '../types/playlist'

const router = useRouter()
const playlists = ref<PlaylistSummary[]>([])
const loading = ref(false)
const error = ref<string | null>(null)
const name = ref('')
const description = ref('')
const showCreate = ref(false)

const load = async (): Promise<void> => {
  loading.value = true
  error.value = null
  try {
    const result = await fetchPlaylists(1, 50)
    playlists.value = result.items
  } catch (e) {
    error.value = e instanceof Error ? e.message : '取得に失敗しました'
  } finally {
    loading.value = false
  }
}

onMounted(() => { void load() })

const submitCreate = async (): Promise<void> => {
  if (!name.value.trim()) return
  try {
    const created = await createPlaylist({
      name: name.value.trim(),
      description: description.value || null,
    })
    name.value = ''
    description.value = ''
    showCreate.value = false
    router.push(`/playlists/${created.playlist_id}/edit`)
  } catch (e) {
    error.value = e instanceof Error ? e.message : '作成に失敗しました'
  }
}
</script>

<template>
  <div class="container">
    <div class="toolbar">
      <h1>プレイリスト</h1>
      <button class="btn" @click="showCreate = !showCreate">
        {{ showCreate ? '閉じる' : '新規作成' }}
      </button>
    </div>

    <p v-if="error" class="error-banner">{{ error }}</p>

    <form v-if="showCreate" class="card form" @submit.prevent="submitCreate">
      <div class="field">
        <label>名前</label>
        <input v-model="name" required maxlength="500" />
      </div>
      <div class="field">
        <label>説明</label>
        <textarea v-model="description" />
      </div>
      <button class="btn" type="submit">作成</button>
    </form>

    <p v-if="loading">読み込み中...</p>
    <p v-else-if="playlists.length === 0" class="empty card">プレイリストがありません</p>

    <ul v-else class="list">
      <li v-for="p in playlists" :key="p.playlist_id" class="card item">
        <div class="info">
          <h3>{{ p.name }}</h3>
          <p v-if="p.description" class="desc">{{ p.description }}</p>
          <p class="meta">{{ p.item_count }} 本</p>
        </div>
        <div class="actions">
          <RouterLink
            :to="`/playlists/${p.playlist_id}/play`"
            class="btn btn-secondary"
          >
            再生
          </RouterLink>
          <RouterLink
            :to="`/playlists/${p.playlist_id}/edit`"
            class="btn btn-ghost"
          >
            編集
          </RouterLink>
        </div>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
}

.toolbar h1 {
  margin: 0;
  font-size: 1.5rem;
}

.form {
  margin-bottom: 16px;
}

.list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: grid;
  gap: 10px;
}

.item {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

@media (min-width: 640px) {
  .item {
    flex-direction: row;
    align-items: center;
    justify-content: space-between;
  }
}

.info h3 {
  margin: 0 0 4px;
  font-size: 1rem;
}

.desc,
.meta {
  margin: 0;
  font-size: 0.875rem;
  color: var(--muted);
}

.actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.empty {
  text-align: center;
  color: var(--muted);
}
</style>
