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
.admin-page{max-width:980px;padding-top:48px}.heading{margin-bottom:28px}h1{margin:0 0 6px}.heading p{margin:0;color:$color-text-secondary}.stats-grid{display:grid;grid-template-columns:repeat(5,1fr);gap:14px;min-height:120px}.stat-card{padding:22px;display:grid;gap:8px}.stat-card span{color:$color-text-secondary;font-size:14px}.stat-card strong{font-size:30px;color:$color-sage-dark}.actions{margin-top:22px;display:flex;gap:12px}@media(max-width:$breakpoint-sm){.stats-grid{grid-template-columns:repeat(2,1fr)}}
</style>
