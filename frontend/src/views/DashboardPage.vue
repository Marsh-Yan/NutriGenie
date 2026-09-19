<script setup lang="ts">
import { computed, onMounted, onUnmounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import EmptyState from '@/components/common/EmptyState.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import ProgressStepper from '@/components/plan/ProgressStepper.vue'
import TodayMeals from '@/components/plan/TodayMeals.vue'
import { useAuthStore } from '@/stores/auth'
import { useDashboardStore } from '@/stores/dashboard'
import { useExecutionStore } from '@/stores/execution'
import { usePlanIndexStore } from '@/stores/planIndex'
import { usePlanStore } from '@/stores/plan'
import { useShoppingStateStore } from '@/stores/shoppingState'
import ExecutionSyncNotice from '@/components/plan/ExecutionSyncNotice.vue'
import type { MealExecutionStatus } from '@/types/localState'

const router = useRouter()
const authStore = useAuthStore()
const dashboardStore = useDashboardStore()
const executionStore = useExecutionStore()
const planIndexStore = usePlanIndexStore()
const planStore = usePlanStore()
const shoppingStateStore = useShoppingStateStore()

const displayName = computed(() => authStore.user?.nickname || '你好')
const currentPlan = computed(() => planIndexStore.items.find(item => item.planId === dashboardStore.currentPlanId) || null)
const todayPlan = computed(() => {
  const days = planStore.result?.weekly_plan || []
  return days.find(day => Object.entries(day.meals).some(([slot, meal]) => meal && executionStore.statusFor(day.day, slot) === 'pending')) || days[0]
})
const shoppingTotal = computed(() => Object.values(planStore.result?.shopping_list.by_category || {}).reduce((sum, items) => sum + items.length, 0))

onMounted(() => {
  const userId = authStore.user?.user_id
  if (!userId) return
  planIndexStore.hydrate(userId)
  dashboardStore.hydrate(userId)
  const planId = dashboardStore.currentPlanId
  if (!planId || !planIndexStore.items.some(item => item.planId === planId)) {
    dashboardStore.selectPlan(null)
    return
  }
  executionStore.hydrate(userId, planId)
  void executionStore.loadServer()
  shoppingStateStore.hydrate(userId, planId)
  planStore.load(planId)
})

watch(() => planStore.status, status => {
  if (!dashboardStore.currentPlanId) return
  planIndexStore.update(dashboardStore.currentPlanId, {
    status,
    completedAt: status === 'completed' ? new Date().toISOString() : null,
  })
})

onUnmounted(() => planStore.stopPolling())

function setMealStatus(day: number, slot: string, status: MealExecutionStatus) {
  executionStore.setStatus(day, slot, status)
}

function openCurrent(tab = 'today') {
  if (!dashboardStore.currentPlanId) return
  router.push({ path: `/plan/${dashboardStore.currentPlanId}`, query: { tab } })
}

function openRecipe(recipeId: string) {
  if (!dashboardStore.currentPlanId) return
  router.push({ name: 'recipe-detail', params: { id: recipeId }, query: { plan: dashboardStore.currentPlanId } })
}
</script>

<template>
  <div class="dashboard-page page-container">
    <PageHeader
      kicker="今日安排"
      :title="`${displayName}，从下一餐继续。`"
      description="餐食执行状态保存在账户中，购物勾选保存在当前设备。"
    >
      <template #actions>
        <el-button type="primary" @click="router.push('/plan/new')">创建计划</el-button>
      </template>
    </PageHeader>

    <EmptyState
      v-if="!currentPlan"
      icon="timeline"
      title="本设备还没有当前计划"
      description="创建一份新计划，或从账户计划列表中选择一份继续执行。"
    >
      <template #actions>
        <el-button type="primary" @click="router.push('/plans')">查看我的计划</el-button>
        <el-button @click="router.push('/plan/new')">创建新计划</el-button>
      </template>
    </EmptyState>

    <template v-else>
      <section class="current-plan-card card">
        <div>
          <span>当前计划 · {{ currentPlan.durationDays }} 天</span>
          <h2>{{ currentPlan.title }}</h2>
          <p v-if="currentPlan.userInput">{{ currentPlan.userInput }}</p>
        </div>
        <el-button type="primary" @click="openCurrent()">打开完整计划</el-button>
      </section>

      <section v-if="!planStore.result && planStore.status !== 'failed'" class="loading-card card">
        <ProgressStepper :status="planStore.status" :progress="planStore.progress" />
      </section>

      <section v-else-if="planStore.status === 'failed' && !planStore.result" class="load-error card" role="alert">
        <div><strong>暂时无法读取当前计划</strong><p>{{ planStore.error || '请稍后重试' }}</p></div>
        <el-button @click="planStore.refreshResult()">重新获取</el-button>
      </section>

      <ExecutionSyncNotice v-if="planStore.result" />
      <div v-if="planStore.result && todayPlan" class="dashboard-grid">
        <section class="today-card card">
          <TodayMeals
            :day="todayPlan"
            :status-for="executionStore.statusFor"
            :status-disabled="!executionStore.ready || executionStore.saving"
            @status="setMealStatus"
            @recipe="openRecipe"
          />
        </section>
        <aside class="progress-card card">
          <span class="eyebrow">执行进度</span>
          <h2>今天完成到哪里了？</h2>
          <div class="progress-stat"><strong>{{ executionStore.handledCount }}</strong><span>餐已记录状态</span></div>
          <div class="progress-stat"><strong>{{ shoppingStateStore.checkedKeys.length }}/{{ shoppingTotal }}</strong><span>项食材已备齐</span></div>
          <p>餐食状态已同步到账户；购物勾选仍仅保存在本设备。</p>
          <el-button plain @click="openCurrent('shopping')">继续采购</el-button>
        </aside>
      </div>
    </template>
  </div>
</template>

<style scoped lang="scss">
.dashboard-page { padding-block: clamp(34px, 5vw, 62px) 96px; }
.current-plan-card { display: flex; align-items: center; justify-content: space-between; gap: 28px; margin-bottom: 18px; padding: 24px 28px; background: linear-gradient(135deg, $color-surface-muted, $color-surface-warm); }
.current-plan-card div { min-width: 0; }
.current-plan-card span { color: $color-sage-dark; font-size: 13px; font-weight: 800; }
.current-plan-card h2 { margin-top: 5px; font-size: 24px; letter-spacing: -.03em; }
.current-plan-card p { display: -webkit-box; max-width: 760px; margin-top: 6px; overflow: hidden; color: $color-text-secondary; font-size: 14px; -webkit-box-orient: vertical; -webkit-line-clamp: 2; }
.loading-card { padding: 22px; }
.load-error { display: flex; align-items: center; justify-content: space-between; gap: 20px; padding: 24px; }
.load-error strong { font-size: 18px; }
.load-error p { margin-top: 5px; color: $color-danger; font-size: 13px; }
.dashboard-grid { display: grid; grid-template-columns: minmax(0, 1.6fr) minmax(280px, .6fr); gap: 18px; align-items: start; }
.today-card, .progress-card { padding: clamp(20px, 3vw, 30px); }
.progress-card { display: grid; gap: 14px; position: sticky; top: 92px; }
.progress-card h2 { font-size: 24px; letter-spacing: -.035em; }
.progress-stat { display: grid; gap: 2px; padding: 16px; border-radius: $radius-md; background: $color-surface-soft; }
.progress-stat strong { color: $color-sage-dark; font-size: 28px; font-variant-numeric: tabular-nums; }
.progress-stat span, .progress-card > p { color: $color-text-secondary; font-size: 13px; line-height: 1.6; }

@media (max-width: $breakpoint-lg) {
  .dashboard-grid { grid-template-columns: 1fr; }
  .progress-card { position: static; }
}

@media (max-width: $breakpoint-sm) {
  .dashboard-page { padding-block: 24px 64px; }
  .current-plan-card, .load-error { align-items: stretch; flex-direction: column; }
  .current-plan-card .el-button { width: 100%; }
}
</style>
