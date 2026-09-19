<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import EmptyState from '@/components/common/EmptyState.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import { clonePlan, getPlanPage, getPlanResult, updatePlanMetadata } from '@/api/plans'
import { useAuthStore } from '@/stores/auth'
import { useDashboardStore } from '@/stores/dashboard'
import { usePlanIndexStore } from '@/stores/planIndex'
import { usePlanStore } from '@/stores/plan'
import type { PlanSummary } from '@/types'

const router = useRouter()
const auth = useAuthStore()
const dashboard = useDashboardStore()
const localIndex = usePlanIndexStore()
const planStore = usePlanStore()
const items = ref<PlanSummary[]>([])
const total = ref(0)
const page = ref(1)
const archived = ref(false)
const loading = ref(false)
const workingId = ref<number | null>(null)
const error = ref('')
const renameTarget = ref<PlanSummary | null>(null)
const renameTitle = ref('')
const renameError = ref('')
let loadVersion = 0
const statusLabel = { pending: '等待中', running: '生成中', completed: '已完成', failed: '失败' }
const statusType = { pending: 'info', running: 'warning', completed: 'success', failed: 'danger' } as const

onMounted(() => {
  if (auth.user?.user_id) {
    localIndex.hydrate(auth.user.user_id)
    dashboard.hydrate(auth.user.user_id)
    void load()
  }
})
watch(archived, () => { page.value = 1; void load() })

async function load() {
  const requestedVersion = ++loadVersion
  loading.value = true
  error.value = ''
  try {
    const result = await getPlanPage(page.value, archived.value)
    if (requestedVersion !== loadVersion) return
    items.value = result.items
    total.value = result.total
  } catch (cause) {
    if (requestedVersion !== loadVersion) return
    error.value = cause instanceof Error ? cause.message : '计划加载失败'
    items.value = []
  } finally {
    if (requestedVersion === loadVersion) loading.value = false
  }
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat('zh-CN', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value))
}

async function openPlan(plan: PlanSummary) {
  if (!auth.user?.user_id) return
  const local = localIndex.items.find(item => item.planId === plan.plan_id)
  localIndex.upsert({
    planId: plan.plan_id, title: plan.title, userInput: local?.userInput || '',
    durationDays: plan.duration_days, totalBudget: plan.total_budget,
    status: plan.status, createdAt: plan.created_at, completedAt: plan.completed_at,
    lastOpenedAt: new Date().toISOString(), sourcePlanId: plan.source_plan_id || undefined,
  })
  dashboard.selectPlan(plan.plan_id)
  await router.push({ path: `/plan/${plan.plan_id}`, query: { tab: 'today' } })
}

async function recreate(plan: PlanSummary) {
  workingId.value = plan.plan_id
  try {
    const detail = await getPlanResult(plan.plan_id)
    if (!detail.user_input) throw new Error('这份计划暂时无法读取原始条件')
    planStore.draftInput = detail.user_input
    planStore.draftDurationDays = plan.duration_days
    planStore.draftTotalBudget = plan.total_budget
    planStore.draftExampleIndex = -1
    await router.push({ name: 'plan-new', query: { source: plan.plan_id } })
  } catch (cause) {
    ElMessage.error(cause instanceof Error ? cause.message : '读取原始条件失败')
  } finally {
    workingId.value = null
  }
}

function startRename(plan: PlanSummary) {
  renameTarget.value = plan
  renameTitle.value = plan.title
  renameError.value = ''
}

function onRenameVisible(value: boolean) {
  if (!value) renameTarget.value = null
}

async function saveRename() {
  const plan = renameTarget.value
  const title = renameTitle.value.trim()
  if (!plan) return
  if (!title) { renameError.value = '请输入计划名称'; return }
  workingId.value = plan.plan_id
  renameError.value = ''
  try {
    await updatePlanMetadata(plan.plan_id, { title })
    localIndex.update(plan.plan_id, { title })
    renameTarget.value = null
    ElMessage.success('名称已保存')
    await load()
  } catch (cause) {
    renameError.value = cause instanceof Error ? cause.message : '保存失败'
  } finally {
    workingId.value = null
  }
}

async function toggleArchive(plan: PlanSummary) {
  const action = archived.value ? '恢复' : '归档'
  if (!window.confirm(`${action}“${plan.title}”？方案内容不会删除。`)) return
  workingId.value = plan.plan_id
  try {
    await updatePlanMetadata(plan.plan_id, { archived: !archived.value })
    if (!archived.value && dashboard.currentPlanId === plan.plan_id) dashboard.selectPlan(null)
    ElMessage.success(`已${action}`)
    await load()
  } catch (cause) {
    ElMessage.error(cause instanceof Error ? cause.message : `${action}失败`)
  } finally {
    workingId.value = null
  }
}

async function duplicate(plan: PlanSummary) {
  if (!window.confirm(`复制“${plan.title}”并生成新计划？这会启动一次新的规划任务。`)) return
  workingId.value = plan.plan_id
  try {
    const created = await clonePlan(plan.plan_id)
    ElMessage.success('新计划已创建')
    await router.push(`/plan/${created.plan_id}`)
  } catch (cause) {
    ElMessage.error(cause instanceof Error ? cause.message : '复制失败')
  } finally {
    workingId.value = null
  }
}

function clearLocalIndex() {
  if (!window.confirm('清空当前账号在本设备上的入口缓存？服务端方案不会被删除。')) return
  localIndex.clear()
  dashboard.selectPlan(null)
  ElMessage.success('本机入口缓存已清空')
}
</script>

<template>
  <div class="history-page page-container">
    <PageHeader
      kicker="我的计划"
      title="随时回到上一份计划。"
      description="计划保存在账户中，可在其他设备打开；本机仍保留当前计划入口与采购勾选。"
    >
      <template #actions>
        <el-button v-if="localIndex.items.length" plain @click="clearLocalIndex">清空本机入口缓存</el-button>
        <el-button type="primary" @click="router.push('/plan/new')">创建新计划</el-button>
      </template>
    </PageHeader>

    <div class="list-toolbar">
      <el-radio-group v-model="archived" aria-label="计划归档筛选">
        <el-radio-button :value="false">进行中</el-radio-button>
        <el-radio-button :value="true">已归档</el-radio-button>
      </el-radio-group>
      <span>共 {{ total }} 份</span>
    </div>

    <div v-if="error" class="list-error" role="alert">
      <span>无法读取账户计划：{{ error }}</span>
      <el-button @click="load">重试</el-button>
    </div>
    <p v-else-if="loading" class="list-loading" role="status">正在读取账户计划…</p>
    <EmptyState
      v-else-if="!items.length"
      icon="timeline"
      :title="archived ? '还没有归档的计划' : '还没有计划'"
      :description="archived ? '归档的计划会显示在这里，也可以随时恢复。' : '创建计划后，无论在哪台设备登录都能从这里找到。'"
    >
      <template v-if="!archived" #actions>
        <el-button type="primary" @click="router.push('/plan/new')">创建第一份计划</el-button>
      </template>
    </EmptyState>

    <section v-else class="plan-list" aria-label="账户计划列表">
      <article v-for="plan in items" :key="plan.plan_id" class="plan-row card">
        <div class="plan-main">
          <div class="plan-title-row">
            <h2>{{ plan.title }}</h2>
            <el-tag :type="statusType[plan.status]" effect="light">{{ statusLabel[plan.status] }}</el-tag>
          </div>
          <div class="plan-meta">
            <time :datetime="plan.created_at">{{ formatDate(plan.created_at) }}</time>
            <span>{{ plan.duration_days }} 天</span>
            <span>{{ plan.total_budget ? `预算 ¥${plan.total_budget}` : '预算不限' }}</span>
            <span v-if="plan.source_plan_id">复制自 #{{ plan.source_plan_id }}</span>
          </div>
        </div>
        <div class="plan-actions">
          <el-button :disabled="workingId === plan.plan_id" @click="startRename(plan)">重命名</el-button>
          <el-button :disabled="workingId === plan.plan_id" @click="toggleArchive(plan)">{{ archived ? '恢复' : '归档' }}</el-button>
          <el-button v-if="plan.status === 'completed'" :loading="workingId === plan.plan_id" @click="recreate(plan)">按原条件重建</el-button>
          <el-button v-if="plan.status === 'completed'" :loading="workingId === plan.plan_id" @click="duplicate(plan)">复制计划</el-button>
          <el-button type="primary" :disabled="workingId === plan.plan_id" @click="openPlan(plan)">打开计划</el-button>
        </div>
      </article>
    </section>

    <el-pagination
      v-if="total > 20"
      v-model:current-page="page"
      class="list-pagination"
      background
      layout="prev, pager, next"
      :page-size="20"
      :total="total"
      @current-change="load"
    />

    <el-dialog :model-value="!!renameTarget" title="重命名计划" width="min(92vw, 440px)" @update:model-value="onRenameVisible">
      <label class="rename-label" for="plan-title">计划名称</label>
      <el-input id="plan-title" v-model="renameTitle" maxlength="100" show-word-limit @keyup.enter="saveRename" />
      <p v-if="renameError" class="rename-error" role="alert">{{ renameError }}</p>
      <template #footer>
        <el-button @click="renameTarget = null">取消</el-button>
        <el-button type="primary" :loading="workingId !== null" @click="saveRename">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped lang="scss">
.history-page { padding-block: clamp(34px, 5vw, 62px) 96px; }
.list-toolbar { display: flex; align-items: center; justify-content: space-between; gap: 16px; margin: 0 0 24px; color: $color-text-secondary; }
.list-error { display: flex; align-items: center; justify-content: space-between; gap: 16px; padding: 20px; border: 1px solid $color-border; border-radius: 14px; color: $color-danger; }
.list-loading { padding: 28px; color: $color-text-secondary; }
.plan-list { display: grid; gap: 14px; }
.plan-row { display: grid; grid-template-columns: minmax(0, 1fr) auto; align-items: center; gap: 24px; padding: 24px; border-color: rgba($color-sage-dark, .11); background: linear-gradient(135deg, rgba($color-card, .98), rgba($color-surface-soft, .62)); }
.plan-main { min-width: 0; }
.plan-title-row { display: flex; align-items: center; gap: 12px; }
.plan-title-row h2 { overflow-wrap: anywhere; font-size: 20px; letter-spacing: -.025em; }
.plan-meta { display: flex; flex-wrap: wrap; gap: 9px 18px; margin-top: 14px; color: $color-text-secondary; font-size: 14px; }
.plan-actions { display: flex; flex-wrap: wrap; justify-content: flex-end; gap: 8px; max-width: 470px; }
.plan-actions .el-button { margin: 0; min-height: 44px; }
.list-pagination { justify-content: center; margin-top: 28px; }
.rename-label { display: block; margin-bottom: 8px; font-weight: 700; }
.rename-error { margin-top: 8px; color: $color-danger; }
@media (max-width: $breakpoint-sm) {
  .history-page { padding-block: 24px 64px; }
  .plan-row { grid-template-columns: 1fr; gap: 18px; padding: 20px; }
  .plan-actions { justify-content: flex-start; max-width: none; }
}
</style>
