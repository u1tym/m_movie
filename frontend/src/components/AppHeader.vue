<script setup lang="ts">
import { RouterLink } from 'vue-router'

const menuUrl = '/mobile/login/#/menu'
</script>

<template>
  <header class="header">
    <div class="container header-inner">
      <div class="header-start">
        <a :href="menuUrl" class="back-btn">← 戻る</a>
        <RouterLink to="/" class="logo">動画</RouterLink>
      </div>
      <nav class="nav">
        <RouterLink to="/">一覧</RouterLink>
        <RouterLink to="/register">登録</RouterLink>
        <RouterLink to="/genres">ジャンル</RouterLink>
      </nav>
    </div>
  </header>
</template>

<style scoped>
.header {
  position: sticky;
  top: 0;
  z-index: 10;
  background: rgba(15, 17, 21, 0.92);
  backdrop-filter: blur(8px);
  border-bottom: 1px solid var(--border);
}

.header-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding-top: 12px;
  padding-bottom: 12px;
}

.header-start {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.back-btn {
  flex-shrink: 0;
  min-height: 36px;
  padding: 0 10px;
  display: inline-flex;
  align-items: center;
  border-radius: 8px;
  border: 1px solid var(--border);
  color: var(--muted);
  font-size: 0.875rem;
  background: transparent;
}

.back-btn:hover {
  color: var(--text);
  background: var(--surface-2);
}

.logo {
  font-size: 1.125rem;
  font-weight: 700;
}

.nav {
  display: flex;
  gap: 8px;
}

.nav a {
  min-height: 36px;
  padding: 0 12px;
  display: inline-flex;
  align-items: center;
  border-radius: 8px;
  color: var(--muted);
  font-size: 0.875rem;
}

.nav a.router-link-active {
  background: var(--surface-2);
  color: var(--text);
}
</style>
