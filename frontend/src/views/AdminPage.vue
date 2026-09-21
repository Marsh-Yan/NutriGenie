<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { getOverview, type AdminOverview } from '@/api/admin'

const overview = ref<AdminOverview | null>(null)
const loading = ref(true)
const error = ref('')
const stats = computed(() => [
  ['注册用户', overview.value?.users],
  ['用户画像', overview.value?.profiles],
  ['菜谱', overview.value?.recipes],
  ['食材', overview.value?.ingredients],
  ['生成方案', overview.value?.plans],
])

async function loadOverview() {
  loading.value = true
  error.value = ''
  try { overview.value = await getOverview() }
  catch (e: any) { error.value = e.message || '无法加载管理数据' }
  finally { loading.value = false }
}

onMounted(loadOverview)
</script>

<template>
  <div class="admin-page page-container">
    <div class="heading"><h1>管理后台</h1><p>NutriGenie 本地运营概览</p></div>
    <el-alert v-if="error" :title="error" type="error" :closable="false" show-icon>
      <template #default><el-button link type="primary" @click="loadOverview">重新加载</el-button></template>
    </el-alert>
    <div v-else v-loading="loading" class="stats-grid">
      <div v-for="item in stats" :key="item[0]" class="stat-card card"><span>{{ item[0] }}</span><strong>{{ item[1] ?? '-' }}</strong></div>
    </div>
    <nav class="actions" aria-label="管理功能">
      <router-link to="/admin/ingredients">维护食材库</router-link>
      <router-link to="/admin/recipes">维护菜谱库</router-link>
      <router-link to="/admin/knowledge">知识库工具</router-link>
    </nav>
  </div>
</template>

<style scoped lang="scss">
.admin-page { max-width: 1200px; padding-top: 44px; padding-bottom: 88px; }
.heading { position: relative; margin-bottom: 22px; padding: 36px; overflow: hidden; border: 1px solid rgba($color-sage,.16); border-radius: $radius-xl; background: linear-gradient(135deg, $color-sage-light, $color-blue-soft 54%, $color-rose-light); box-shadow: $shadow-md; }
.heading::after { position: absolute; right: -60px; bottom: -100px; width: 260px; height: 260px; border: 1px solid rgba($color-sage,.15); border-radius: 50%; content: ''; }
h1 { margin: 0 0 7px; color: $color-text-primary; font-size: clamp(30px,4vw,44px); letter-spacing: -.045em; }
.heading p { margin: 0; color: $color-text-secondary; }
.stats-grid { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 12px; min-height: 140px; }
.stat-card { position: relative; display: grid; gap: 18px; padding: 24px; overflow: hidden; box-shadow: none; }
.stat-card::before { position: absolute; top: 0; right: 0; left: 0; height: 4px; background: $color-sage; content: ''; }
.stat-card:nth-child(2)::before { background: $color-rose; }.stat-card:nth-child(3)::before { background: $color-blue; }.stat-card:nth-child(4)::before { background: $color-butter; }.stat-card:nth-child(5)::before { background: $color-lime; }
.stat-card span { color: $color-text-secondary; font-size: 13px; font-weight: 650; }
.stat-card strong { color: $color-text-primary; font-size: clamp(30px,3vw,40px); letter-spacing: -.04em; }
.actions { display: flex; gap: 10px; margin-top: 20px; padding: 16px; border: 1px solid rgba($color-sage-dark,.1); border-radius: $radius-lg; background: rgba(255,255,255,.72); }
.actions a { display: inline-flex; min-height: 44px; align-items: center; padding: 9px 16px; border: 1px solid $color-border; border-radius: $radius-sm; background: $color-surface; color: $color-brand; font-size: 14px; font-weight: 750; }
.actions a:first-child { border-color: $color-brand; background: $color-brand; color: $color-text-inverse; }
.actions a:hover { border-color: $color-sage; background: $color-surface-soft; color: $color-brand; }
.actions a:first-child:hover { border-color: $color-brand-hover; background: $color-brand-hover; color: $color-text-inverse; }
@media (max-width: $breakpoint-lg) { .stats-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); } }
@media (max-width: $breakpoint-sm) {
  .admin-page { padding-top: 24px; }
  .heading { padding: 28px 22px; }
  .stats-grid { grid-template-columns: repeat(2, minmax(0,1fr)); }
  .stat-card { padding: 18px; }
  .actions { align-items: stretch; flex-direction: column; }
  .actions a { width: 100%; justify-content: center; }
}
</style>
