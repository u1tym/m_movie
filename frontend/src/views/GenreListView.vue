<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { createGenre, fetchGenres } from '../api/movie'
import type { Genre } from '../types/movie'

const genres = ref<Genre[]>([])
const loading = ref(false)
const error = ref<string | null>(null)
const name = ref('')
const sortOrder = ref(0)

const load = async (): Promise<void> => {
  loading.value = true
  error.value = null
  try {
    const result = await fetchGenres()
    genres.value = result.items
  } catch (e) {
    error.value = e instanceof Error ? e.message : '取得に失敗しました'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  void load()
})

const submit = async (): Promise<void> => {
  if (!name.value.trim()) return
  error.value = null
  try {
    await createGenre({ name: name.value.trim(), sort_order: sortOrder.value })
    name.value = ''
    sortOrder.value = 0
    await load()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '追加に失敗しました'
  }
}
</script>

<template>
  <div class="container">
    <h1>ジャンル管理</h1>
    <p class="note">システム共通ジャンルに加え、ユーザー独自のジャンルを追加できます。</p>
    <p v-if="error" class="error-banner">{{ error }}</p>

    <form class="card form" @submit.prevent="submit">
      <div class="field">
        <label>ジャンル名</label>
        <input v-model="name" required maxlength="100" />
      </div>
      <div class="field">
        <label>表示順</label>
        <input v-model.number="sortOrder" type="number" min="0" />
      </div>
      <button class="btn" type="submit">追加</button>
    </form>

    <section class="list">
      <h2>一覧</h2>
      <p v-if="loading">読み込み中...</p>
      <ul v-else class="genre-list">
        <li v-for="g in genres" :key="g.genre_id" class="card item">
          <span>{{ g.name }}</span>
          <span class="chip">{{ g.is_system ? 'システム' : 'ユーザー' }}</span>
        </li>
      </ul>
    </section>
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
  margin-bottom: 20px;
}

.list h2 {
  font-size: 1rem;
  margin: 0 0 10px;
}

.genre-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: grid;
  gap: 8px;
}

.item {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
</style>
