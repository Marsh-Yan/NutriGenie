<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import EmptyState from '@/components/common/EmptyState.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import { useAuthStore } from '@/stores/auth'
import { useDashboardStore } from '@/stores/dashboard'
import { usePlanIndexStore } from '@/stores/planIndex'
import { usePlanStore } from '@/stores/plan'
import type { LocalPlanIndexItem } from '@/types/localState'

const router = useRouter()
const authStore = useAuthStore()
const dashboardStore = useDashboardStore()
const planIndexStore = usePlanIndexStore()
const planStore = usePlanStore()

const statusLabel = { pending: '等待中', running: '生成中', completed: '已完成', failed: '失败' }
const statusType = { pending: 'info', running: 'warning', completed: 'success', failed: 'danger' } as const

onMounted(() => {
  const userId = authStore.user?.user_id
  if (!userId) return
  planIndexStore.hydrate(userId)
  dashboardStore.hydrate(userId)
})

function formatDate(value: string) {
  return new Intl.DateTimeFormat('zh-CN', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value))
}

function openPlan(plan: LocalPlanIndexItem) {
  planIndexStore.touch(plan.planId)
  dashboardStore.selectPlan(plan.planId)
  router.push({ path: `/plan/${plan.planId}`, query: { tab: 'today' } })
}

function recreate(plan: LocalPlanIndexItem) {
  planStore.draftInput = plan.userInput
  planStore.draftDurationDays = plan.durationDays
  planStore.draftTotalBudget = plan.totalBudget
  planStore.draftExampleIndex = -1
  router.push({ name: 'plan-new', query: { source: plan.planId } })
}

function clearLocalIndex() {
  if (!window.confirm('清空当前账号在本设备上的计划记录？服务端方案不会被删除。')) return
  planIndexStore.clear()
  dashboardStore.selectPlan(null)
}
</script>

<template>
  <div class="history-page page-container">
    <PageHeader
      kicker="本地计划记录"
      title="随时回到上一份计划，也能按原条件重新开始。"
      description="这里只展示当前账号在本设备创建过的计划。方案内容仍由服务端保存，本地仅记录入口与执行进度。"
    >
      <template #actions>
        <el-button v-if="planIndexStore.items.length" plain @click="clearLocalIndex">清空本地记录</el-button>
        <el-button type="primary" @click="router.push('/plan/new')">创建新计划</el-button>
      </template>
    </PageHeader>

    <p class="local-notice">本地进度仅保存在本设备，并按当前账号隔离。</p>

    <EmptyState
      v-if="!planIndexStore.sortedItems.length"
      icon="timeline"
      title="本设备还没有计划记录"
      description="创建计划后，这里会保存标题、创建时间与执行入口。清空浏览器数据后记录会消失。"
    >
      <template #actions>
        <el-button type="primary" @click="router.push('/plan/new')">创建第一份计划</el-button>
      </template>
    </EmptyState>

    <section v-else class="plan-list" aria-label="本地计划列表">
      <article v-for="plan in planIndexStore.sortedItems" :key="plan.planId" class="plan-row card">
        <div class="plan-main">
          <div class="plan-title-row">
            <h2>{{ plan.title }}</h2>
            <el-tag :type="statusType[plan.status]" effect="light">{{ statusLabel[plan.status] }}</el-tag>
          </div>
          <p>{{ plan.userInput }}</p>
          <div class="plan-meta">
            <time :datetime="plan.createdAt">{{ formatDate(plan.createdAt) }}</time>
            <span>{{ plan.durationDays }} 天</span>
            <span>{{ plan.totalBudget ? `预算 ¥${plan.totalBudget}` : '预算不限' }}</span>
          </div>
        </div>
        <div class="plan-actions">
          <el-button plain @click="recreate(plan)">按原条件重建</el-button>
          <el-button type="primary" @click="openPlan(plan)">打开计划</el-button>
        </div>
      </article>
    </section>
  </div>
</template>

<style scoped lang="scss">
.history-page { padding-block: clamp(34px, 5vw, 62px) 96px; }
.local-notice { margin: -10px 0 24px; color: $color-text-secondary; font-size: 13px; text-align: right; }
.plan-list { display: grid; gap: 14px; }
.plan-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: 28px;
  padding: 24px;
  border-color: rgba($color-sage-dark, .11);
  background: linear-gradient(135deg, rgba($color-card, .98), rgba($color-surface-soft, .62));
}
.plan-main { min-width: 0; }
.plan-title-row { display: flex; align-items: center; gap: 12px; }
.plan-title-row h2 { overflow: hidden; font-size: 20px; letter-spacing: -.025em; text-overflow: ellipsis; white-space: nowrap; }
.plan-main > p { display: -webkit-box; max-width: 800px; margin-top: 9px; overflow: hidden; color: $color-text-secondary; font-size: 14px; line-height: 1.65; -webkit-box-orient: vertical; -webkit-line-clamp: 2; }
.plan-meta { display: flex; flex-wrap: wrap; gap: 9px 18px; margin-top: 14px; color: $color-text-placeholder; font-size: 13px; font-weight: 650; }
.plan-actions { display: flex; gap: 9px; }

@media (max-width: $breakpoint-sm) {
  .history-page { padding-block: 24px 64px; }
  .local-notice { margin-top: 0; text-align: left; }
  .plan-row { grid-template-columns: 1fr; gap: 18px; padding: 20px; }
  .plan-title-row { align-items: flex-start; justify-content: space-between; }
  .plan-title-row h2 { white-space: normal; }
  .plan-actions { display: grid; grid-template-columns: 1fr 1fr; }
  .plan-actions .el-button { width: 100%; margin: 0; }
}
</style>
