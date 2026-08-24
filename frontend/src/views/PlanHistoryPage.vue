<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { getPlans } from '@/api/plans'
import type { PlanListItem } from '@/types'

const router = useRouter()
const plans = ref<PlanListItem[]>([])
const loading = ref(true)
const error = ref('')

const statusLabel = { pending: '等待中', running: '生成中', completed: '已完成', failed: '失败' }
const statusType = { pending: 'info', running: 'warning', completed: 'success', failed: 'danger' } as const

onMounted(async () => {
  try {
    plans.value = await getPlans()
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : '历史方案加载失败'
  } finally {
    loading.value = false
  }
})

function formatDate(value: string) {
  return new Intl.DateTimeFormat('zh-CN', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value))
}
</script>

<template>
  <div class="history-page page-container">
    <div class="page-heading">
      <div><span class="eyebrow">持续记录，随时回看</span><h1>我的方案</h1></div>
      <el-button type="primary" round @click="router.push('/plan/new')">创建新方案</el-button>
    </div>
    <div v-if="loading" class="state-card card" aria-live="polite">正在加载历史方案…</div>
    <div v-else-if="error" class="state-card card error" role="alert">{{ error }}</div>
    <div v-else-if="!plans.length" class="state-card card">
      <h2>还没有方案</h2><p>描述目标、预算和忌口，生成第一份可执行饮食计划。</p>
      <el-button type="primary" round @click="router.push('/plan/new')">开始规划</el-button>
    </div>
    <div v-else class="plan-list">
      <button v-for="plan in plans" :key="plan.plan_id" class="plan-card card" type="button" @click="router.push(`/plan/${plan.plan_id}`)">
        <div class="plan-card-head">
          <time :datetime="plan.created_at">{{ formatDate(plan.created_at) }}</time>
          <el-tag :type="statusType[plan.status]" effect="light">{{ statusLabel[plan.status] }}</el-tag>
        </div>
        <strong>{{ plan.user_input }}</strong>
        <span>{{ plan.duration_days }} 天 · {{ plan.total_budget ? `预算 ¥${plan.total_budget.toFixed(0)}` : '未限制预算' }}</span>
      </button>
    </div>
  </div>
</template>

<style scoped lang="scss">
.history-page { max-width: 820px; padding-top: 48px; padding-bottom: 80px; }
.page-heading { display: flex; align-items: end; justify-content: space-between; gap: 20px; margin-bottom: 28px; }
.eyebrow { color: $color-sage-dark; font-size: 13px; font-weight: 700; }
h1 { margin-top: 5px; color: $color-text-primary; font-size: 32px; }
.state-card { padding: 40px; text-align: center; color: $color-text-secondary; }
.state-card h2 { color: $color-text-primary; margin-bottom: 8px; }
.state-card p { margin-bottom: 18px; }
.state-card.error { color: $color-danger; }
.plan-list { display: grid; gap: 12px; }
.plan-card { display: grid; gap: 10px; width: 100%; padding: 20px; background: $color-card; color: inherit; text-align: left; cursor: pointer; }
.plan-card:hover { transform: translateY(-2px); }
.plan-card-head { display: flex; align-items: center; justify-content: space-between; }
.plan-card time, .plan-card > span { color: $color-text-secondary; font-size: 13px; }
.plan-card > strong { color: $color-text-primary; font-size: 16px; }
@media (max-width: $breakpoint-sm) { .history-page { padding-top: 28px; } .page-heading { align-items: flex-start; } h1 { font-size: 28px; } }
</style>
