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
    <section class="history-hero" aria-labelledby="history-title">
      <div class="hero-decoration decoration-one" aria-hidden="true" />
      <div class="hero-decoration decoration-two" aria-hidden="true" />
      <div class="hero-copy">
        <span class="hero-kicker"><i aria-hidden="true" />你的营养档案</span>
        <h1 id="history-title">每一份方案，<span>都值得被好好记录。</span></h1>
        <p>回看过去的饮食目标与执行方案，也可以随时从一份新计划重新出发。</p>
      </div>
      <div class="hero-actions">
        <div v-if="!loading && !error" class="plan-count" aria-live="polite">
          <strong>{{ plans.length }}</strong>
          <span>份历史方案</span>
        </div>
        <el-button class="create-plan-btn" type="primary" size="large" round @click="router.push('/plan/new')">
          <span aria-hidden="true">＋</span>创建新方案
        </el-button>
      </div>
    </section>

    <section class="history-content" aria-labelledby="history-list-title">
      <div v-if="!loading && !error && plans.length" class="list-heading">
        <div>
          <span class="eyebrow">方案时间线</span>
          <h2 id="history-list-title">最近创建</h2>
        </div>
        <p>选择任意方案查看菜谱、营养报告和采购清单</p>
      </div>

      <div v-if="loading" class="plan-list loading-grid" aria-live="polite" aria-busy="true">
        <span class="sr-status">正在加载历史方案…</span>
        <div v-for="i in 6" :key="i" class="skeleton-card card" aria-hidden="true">
          <div class="skeleton-line short" />
          <div class="skeleton-line title" />
          <div class="skeleton-line title second" />
          <div class="skeleton-meta"><i /><i /></div>
        </div>
      </div>

      <div v-else-if="error" class="state-card card error" role="alert">
        <div class="state-visual error-visual" aria-hidden="true">!</div>
        <span class="state-kicker">加载遇到问题</span>
        <h2>暂时无法读取历史方案</h2>
        <p>{{ error }}</p>
        <el-button type="primary" round @click="router.push('/plan/new')">先创建一份新方案</el-button>
      </div>

      <div v-else-if="!plans.length" class="state-card card empty">
        <div class="state-visual empty-visual" aria-hidden="true"><span>✦</span></div>
        <span class="state-kicker">从第一步开始</span>
        <h2>这里还没有饮食方案</h2>
        <p>告诉 AI 你的目标、预算和忌口，生成第一份兼顾营养与日常执行的计划。</p>
        <el-button type="primary" size="large" round @click="router.push('/plan/new')">开始我的第一次规划</el-button>
      </div>

      <div v-else class="plan-list">
        <button
          v-for="plan in plans"
          :key="plan.plan_id"
          class="plan-card card"
          :class="`status-${plan.status}`"
          type="button"
          @click="router.push(`/plan/${plan.plan_id}`)"
        >
          <span class="status-accent" aria-hidden="true" />
          <div class="plan-card-head">
            <time :datetime="plan.created_at"><i aria-hidden="true" />{{ formatDate(plan.created_at) }}</time>
            <el-tag :type="statusType[plan.status]" effect="light" size="small">{{ statusLabel[plan.status] }}</el-tag>
          </div>
          <div class="plan-card-copy">
            <span>饮食需求</span>
            <strong>{{ plan.user_input }}</strong>
          </div>
          <div class="plan-meta" aria-label="方案概览">
            <span><b>{{ plan.duration_days }}</b> 天规划</span>
            <span><b>{{ plan.total_budget ? `¥${plan.total_budget.toFixed(0)}` : '不限' }}</b> 总预算</span>
          </div>
          <span class="plan-card-footer">
            <span>打开完整方案</span>
            <i aria-hidden="true">→</i>
          </span>
        </button>
      </div>
    </section>
  </div>
</template>

<style scoped lang="scss">
.history-page { padding-block: clamp(36px, 5vw, 68px) 96px; }

.history-hero {
  position: relative;
  display: flex;
  min-height: 286px;
  overflow: hidden;
  align-items: flex-end;
  justify-content: space-between;
  gap: 40px;
  padding: clamp(34px, 5vw, 64px);
  border: 1px solid rgba($color-sage, .18);
  border-radius: $radius-xl;
  background:
    radial-gradient(circle at 88% 12%, rgba($color-blue-soft, .9), transparent 18rem),
    radial-gradient(circle at 5% 100%, rgba($color-rose-light, .68), transparent 20rem),
    linear-gradient(135deg, #DCE4DD 0%, #EDE4DE 100%);
  box-shadow: $shadow-lg;
  color: $color-text-primary;
}

.hero-decoration {
  position: absolute;
  border: 1px solid rgba($color-sage, .16);
  border-radius: 50%;
  pointer-events: none;
}

.decoration-one { top: -150px; right: -80px; width: 380px; height: 380px; }
.decoration-two { top: 26px; right: 190px; width: 74px; height: 74px; background: rgba($color-peach, .1); }
.hero-copy,
.hero-actions { position: relative; z-index: 1; }

.hero-copy { max-width: 730px; }

.hero-kicker {
  display: inline-flex;
  align-items: center;
  gap: 9px;
  color: $color-sage-dark;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: .12em;
  text-transform: uppercase;
}

.hero-kicker i {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: currentColor;
  box-shadow: 0 0 0 5px rgba($color-sage, .12);
}

.hero-copy h1 {
  margin-top: 15px;
  color: $color-text-primary;
  font-size: clamp(38px, 4.7vw, 62px);
  letter-spacing: -.055em;
  line-height: 1.04;
}

.hero-copy h1 span { color: $color-rose-dark; }

.hero-copy p {
  max-width: 42rem;
  margin-top: 18px;
  color: $color-text-secondary;
  font-size: 14px;
}

.hero-actions {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  gap: 14px;
}

.plan-count {
  display: grid;
  min-width: 92px;
  padding-right: 16px;
  border-right: 1px solid rgba($color-sage, .18);
  text-align: right;
}

.plan-count strong { color: $color-text-primary; font-size: 28px; line-height: 1; }
.plan-count span { margin-top: 5px; color: $color-text-secondary; font-size: 12px; }

.create-plan-btn.el-button {
  border-color: $color-sage-dark;
  background: $color-sage-dark;
  box-shadow: 0 12px 28px rgba(79, 88, 82, .16);
  color: $color-text-inverse;
}

.create-plan-btn.el-button:hover:not(.is-disabled),
.create-plan-btn.el-button:focus-visible {
  border-color: $color-sage;
  background: $color-sage;
  color: $color-text-inverse;
}

.create-plan-btn span[aria-hidden] { margin-right: 4px; font-size: 18px; font-weight: 500; }

.history-content { margin-top: clamp(34px, 5vw, 56px); }

.list-heading {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 28px;
  margin-bottom: 22px;
}

.list-heading h2 {
  margin-top: 7px;
  font-size: clamp(26px, 3vw, 36px);
  letter-spacing: -.04em;
}

.list-heading > p { color: $color-text-secondary; font-size: 12px; }

.plan-list {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 18px;
}

.plan-card {
  --status-color: #{$color-sage};
  position: relative;
  display: flex;
  min-width: 0;
  min-height: 290px;
  overflow: hidden;
  flex-direction: column;
  padding: 25px;
  border: 1px solid rgba($color-sage-dark, .1);
  background: rgba($color-card, .96);
  color: inherit;
  cursor: pointer;
  text-align: left;
}

.plan-card.status-pending { --status-color: #{$color-info}; }
.plan-card.status-running { --status-color: #{$color-warning}; }
.plan-card.status-completed { --status-color: #{$color-success}; }
.plan-card.status-failed { --status-color: #{$color-danger}; }

.status-accent {
  position: absolute;
  top: 0;
  right: 0;
  left: 0;
  height: 4px;
  background: var(--status-color);
  opacity: .8;
}

.plan-card:hover {
  border-color: rgba($color-sage, .34);
  box-shadow: $shadow-md;
  transform: translateY(-6px);
}

.plan-card:focus-visible {
  border-color: $color-sage;
  box-shadow: 0 0 0 4px rgba($color-sage, .12), $shadow-md;
}

.plan-card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.plan-card time {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  color: $color-text-secondary;
  font-size: 12px;
  font-weight: 650;
}

.plan-card time i {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--status-color);
  box-shadow: 0 0 0 4px rgba($color-sage, .08);
}

.plan-card-copy {
  display: grid;
  gap: 9px;
  margin-top: 30px;
}

.plan-card-copy > span {
  color: $color-text-placeholder;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: .1em;
  text-transform: uppercase;
}

.plan-card-copy strong {
  display: -webkit-box;
  overflow: hidden;
  color: $color-text-primary;
  font-size: 18px;
  font-weight: 720;
  letter-spacing: -.02em;
  line-height: 1.5;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 3;
}

.plan-meta {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
  margin-top: 22px;
}

.plan-meta > span {
  display: grid;
  gap: 1px;
  padding: 10px 11px;
  border-radius: $radius-xs;
  background: $color-surface-soft;
  color: $color-text-secondary;
  font-size: 12px;
  font-weight: 550;
}

.plan-meta b { color: $color-text-primary; font-size: 14px; }

.plan-card-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: auto;
  padding-top: 20px;
  color: $color-sage-dark;
  font-size: 13px;
  font-weight: 750;
}

.plan-card-footer i {
  display: grid;
  width: 32px;
  height: 32px;
  place-items: center;
  border-radius: 50%;
  background: $color-lime-soft;
  font-size: 15px;
  font-style: normal;
  transition: transform .2s ease;
}

.plan-card:hover .plan-card-footer i { transform: translateX(3px); }

.state-card {
  display: grid;
  min-height: 420px;
  place-items: center;
  align-content: center;
  padding: 48px 28px;
  background:
    radial-gradient(circle at 50% 0, rgba($color-lime, .15), transparent 18rem),
    rgba($color-card, .95);
  text-align: center;
}

.state-visual {
  display: grid;
  width: 86px;
  height: 86px;
  margin-bottom: 20px;
  place-items: center;
  border-radius: 28px;
  transform: rotate(-4deg);
}

.empty-visual {
  background: $color-lime-soft;
  box-shadow: 12px 12px 0 rgba($color-sage, .08);
  color: $color-sage-dark;
  font-size: 34px;
}

.empty-visual span { transform: rotate(4deg); }

.error-visual {
  border: 1px solid rgba($color-danger, .12);
  background: rgba($color-danger, .08);
  color: $color-danger;
  font-size: 34px;
  font-weight: 800;
}

.state-kicker {
  color: $color-sage-dark;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: .12em;
  text-transform: uppercase;
}

.state-card h2 {
  margin-top: 9px;
  font-size: clamp(25px, 3vw, 34px);
  letter-spacing: -.04em;
}

.state-card p {
  max-width: 31rem;
  margin: 10px auto 24px;
  color: $color-text-secondary;
  font-size: 13px;
}

.state-card.error .state-kicker,
.state-card.error h2 { color: $color-danger; }

.loading-grid { position: relative; }

.sr-status {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0 0 0 0);
  white-space: nowrap;
}

.skeleton-card {
  display: grid;
  min-height: 290px;
  align-content: start;
  gap: 16px;
  padding: 25px;
}

.skeleton-line,
.skeleton-meta i {
  display: block;
  border-radius: 999px;
  background: linear-gradient(90deg, $color-surface-soft 20%, #F8FAF7 48%, $color-surface-soft 78%);
  background-size: 220% 100%;
  animation: skeleton-wave 1.5s ease-in-out infinite;
}

.skeleton-line { height: 12px; }
.skeleton-line.short { width: 38%; height: 9px; margin-bottom: 22px; }
.skeleton-line.title { width: 92%; height: 18px; }
.skeleton-line.second { width: 68%; }
.skeleton-meta { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 20px; }
.skeleton-meta i { height: 52px; border-radius: $radius-xs; }

@keyframes skeleton-wave {
  from { background-position: 100% 0; }
  to { background-position: -100% 0; }
}

@media (max-width: $breakpoint-lg) {
  .history-hero { align-items: flex-start; flex-direction: column; }
  .hero-actions { align-self: stretch; justify-content: flex-end; }
  .plan-list { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}

@media (max-width: $breakpoint-sm) {
  .history-page { padding-block: 24px 56px; }

  .history-hero {
    min-height: auto;
    gap: 28px;
    padding: 30px 22px;
    border-radius: $radius-lg;
  }

  .hero-copy h1 { font-size: 37px; }
  .hero-copy p { margin-top: 14px; font-size: 13px; }

  .hero-actions {
    display: grid;
    grid-template-columns: auto minmax(0, 1fr);
    width: 100%;
    gap: 12px;
  }

  .plan-count { min-width: 70px; padding-right: 12px; text-align: left; }
  .plan-count strong { font-size: 24px; }
  .create-plan-btn { width: 100%; }

  .history-content { margin-top: 34px; }

  .list-heading {
    align-items: flex-start;
    flex-direction: column;
    gap: 8px;
    margin-bottom: 17px;
  }

  .list-heading h2 { font-size: 29px; }
  .plan-list { grid-template-columns: 1fr; gap: 13px; }
  .plan-card { min-height: 260px; padding: 22px; }
  .plan-card-copy { margin-top: 24px; }
  .plan-card-copy strong { font-size: 17px; }

  .state-card { min-height: 390px; padding: 38px 20px; }
  .state-visual { width: 76px; height: 76px; border-radius: 24px; }
  .skeleton-card { min-height: 260px; }
}
</style>
