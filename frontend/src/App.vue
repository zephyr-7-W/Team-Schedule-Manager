<template>
  <div class="app-shell">
    <header class="app-topbar">
      <span class="app-logo">📅 团队日程管理</span>
      <!-- <span class="app-subtitle">Team Schedule · 最简原型（Vue3 + FastAPI + SQLite）</span> -->
    </header>
    <HomeView />
  </div>
</template>

<script setup lang="ts">
import HomeView from './views/HomeView.vue'
</script>

<style scoped>
.app-shell {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.app-topbar {
  height: 48px;
  flex: none;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 16px;
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
}

.app-logo {
  font-size: 16px;
  font-weight: 700;
}

.app-subtitle {
  font-size: 12px;
  color: #909399;
}
</style>
