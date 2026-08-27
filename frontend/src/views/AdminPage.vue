<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { getOverview, type AdminOverview } from '@/api/admin'

const overview = ref<AdminOverview | null>(null)
const loading = ref(true)
const error = ref('')
onMounted(async () => {
  try { overview.value = await getOverview() }
  catch (e: any) { error.value = e.message || '无法加载管理数据' }
  finally { loading.value = false }
})
</script>

<template>
  <div class="admin-page page-container">
    <div class="heading"><h1>管理后台</h1><p>NutriGenie 本地运营概览</p></div>
    <el-alert v-if="error" :title="error" type="error" :closable="false" />
    <div v-else v-loading="loading" class="stats-grid">
      <div v-for="item in [['注册用户', overview?.users], ['用户画像', overview?.profiles], ['菜谱', overview?.recipes], ['食材', overview?.ingredients], ['生成方案', overview?.plans]]" :key="item[0]" class="stat-card card"><span>{{ item[0] }}</span><strong>{{ item[1] ?? '-' }}</strong></div>
    </div>
    <div class="actions"><router-link to="/admin/ingredients"><el-button type="primary">食材库</el-button></router-link><router-link to="/admin/recipes"><el-button>菜谱库</el-button></router-link><router-link to="/admin/knowledge"><el-button>知识库</el-button></router-link></div>
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
@media (max-width: $breakpoint-lg) { .stats-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); } }
@media (max-width: $breakpoint-sm) {
  .admin-page { padding-top: 24px; }
  .heading { padding: 28px 22px; }
  .stats-grid { grid-template-columns: repeat(2, minmax(0,1fr)); }
  .stat-card { padding: 18px; }
  .actions { align-items: stretch; flex-direction: column; }
  .actions :deep(.el-button) { width: 100%; margin: 0; }
}
</style>
