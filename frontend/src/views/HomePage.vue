<script setup lang="ts">
import { useRouter } from 'vue-router'
import PremiumIcon from '@/components/common/PremiumIcon.vue'
import type { PremiumIconName } from '@/components/common/PremiumIcon.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import { useAuthStore } from '@/stores/auth'
import { usePlanStore } from '@/stores/plan'

const router = useRouter()
const auth = useAuthStore()
const planStore = usePlanStore()
function viewExample() {
  router.push('/demo')
}

function startUsing() {
  if (auth.isLoggedIn) router.push('/plan/new')
  else router.push({ name: 'auth', query: { mode: 'register', redirect: '/profile' } })
}

function startWithGoal(prompt: string) {
  planStore.draftInput = prompt
  planStore.draftExampleIndex = -1
  startUsing()
}

const goals: { icon: PremiumIconName; label: string; prompt: string }[] = [
  { icon: 'flame', label: '轻松减脂', prompt: '我想制定一周减脂饮食计划，兼顾饱腹感与日常预算' },
  { icon: 'strength', label: '科学增肌', prompt: '我想制定高蛋白增肌饮食计划，菜谱要简单易执行' },
  { icon: 'blood', label: '平稳控糖', prompt: '我想制定一周控糖饮食计划，减少精制碳水并保证营养均衡' },
  { icon: 'leaf', label: '均衡饮食', prompt: '我想制定一周均衡饮食计划，食材丰富、做法家常' },
]

const weekDays = [
  { day: '一', kcal: '1,820' },
  { day: '二', kcal: '1,790' },
  { day: '三', kcal: '1,860', active: true },
  { day: '四', kcal: '1,805' },
  { day: '五', kcal: '1,835' },
  { day: '六', kcal: '1,910' },
  { day: '日', kcal: '1,875' },
]

const meals = [
  { slot: '早餐', name: '南瓜燕麦蛋奶杯', meta: '520 kcal · 15 分钟', tone: 'citrus' },
  { slot: '午餐', name: '香煎鸡胸藜麦碗', meta: '710 kcal · ¥18', tone: 'leaf' },
  { slot: '晚餐', name: '番茄豆腐菌菇煲', meta: '630 kcal · 25 分钟', tone: 'tomato' },
]

const decisionSteps: { icon: PremiumIconName; title: string; description: string; evidence: string }[] = [
  {
    icon: 'profile',
    title: '先确认不能妥协的条件',
    description: '画像、预算、过敏原、饮食类型和已有食材被整理成清晰约束。',
    evidence: '过敏原作为硬约束',
  },
  {
    icon: 'plan',
    title: '再组合一周的推荐方案',
    description: '结构化候选与语义理解共同工作，营养、预算和偏好由程序确定性核算。',
    evidence: '推荐依据可追溯',
  },
  {
    icon: 'shopping',
    title: '最后变成每天能执行的动作',
    description: '餐单、菜谱步骤与采购清单放在同一条路径里，减少来回整理。',
    evidence: '计划与采购同步查看',
  },
]
</script>

<template>
  <div class="home-page">
    <section class="hero page-container" aria-labelledby="home-title">
      <div class="hero-shell">
        <div class="hero-copy">
          <h1 id="home-title">
            <span>把一周三餐，</span>
            <span>安排得更像</span>
            <span>你的生活。</span>
          </h1>
          <p>
            NutriGenie 把健康目标、预算、忌口和现有食材放进同一份计划，给出看得懂、买得到、做得出的每日安排。
          </p>
          <div class="hero-actions">
            <el-button class="hero-primary-action" size="large" @click="startUsing">创建我的计划</el-button>
            <button class="hero-secondary-action" type="button" @click="viewExample">
              查看完整示例
            </button>
          </div>
          <ul class="trust-list" aria-label="产品保障">
            <li><PremiumIcon name="check" :size="15" :box-size="24" />硬约束优先</li>
            <li><PremiumIcon name="check" :size="15" :box-size="24" />营养与预算可解释</li>
            <li><PremiumIcon name="check" :size="15" :box-size="24" />失败路径可恢复</li>
          </ul>
        </div>

        <div class="plan-preview" aria-label="七天饮食计划示例">
          <div class="plan-preview__header">
            <div>
              <span>本周计划</span>
              <strong>均衡减脂 · 7 天</strong>
            </div>
            <StatusBadge label="校验通过" tone="success" />
          </div>

          <ol class="week-strip" aria-label="每日能量预览">
            <li v-for="item in weekDays" :key="item.day" :class="{ 'is-active': item.active }">
              <span>周{{ item.day }}</span>
              <strong>{{ item.kcal }}</strong>
              <small>kcal</small>
            </li>
          </ol>

          <div class="selected-day">
            <div class="selected-day__heading">
              <div><span>星期三</span><strong>三餐安排</strong></div>
              <small>目标 1,850 kcal</small>
            </div>
            <ol class="meal-list">
              <li v-for="meal in meals" :key="meal.slot">
                <i :class="'tone-' + meal.tone" aria-hidden="true" />
                <span>{{ meal.slot }}</span>
                <strong>{{ meal.name }}</strong>
                <small>{{ meal.meta }}</small>
              </li>
            </ol>
          </div>

          <div class="plan-preview__footer">
            <div><span>本周采购</span><strong>¥286</strong><small>预算 ¥300</small></div>
            <div><span>蛋白质达成</span><strong>96%</strong><small>每日平均</small></div>
            <div><span>食材利用</span><strong>8 项</strong><small>优先消耗</small></div>
          </div>
        </div>
      </div>
    </section>

    <section class="goal-entry page-container" aria-labelledby="goal-title">
      <div class="goal-entry__heading">
        <h2 id="goal-title">你最想先解决哪件事？</h2>
      </div>
      <div class="goal-options">
        <button v-for="goal in goals" :key="goal.label" type="button" @click="startWithGoal(goal.prompt)">
          <PremiumIcon :name="goal.icon" :size="20" :box-size="40" />
          <span>{{ goal.label }}</span>
        </button>
      </div>
    </section>

    <section id="how-it-works" class="decision-section page-container" aria-labelledby="decision-title">
      <div class="decision-intro">
        <h2 id="decision-title">先守住约束，再谈推荐，最后帮助执行。</h2>
        <p>系统不会用“猜你喜欢”覆盖过敏原、预算和营养边界，也不会把一份报告当作终点。</p>
        <router-link to="/demo" class="inline-link">查看一份完整方案</router-link>
      </div>

      <ol class="decision-path">
        <li v-for="(step, index) in decisionSteps" :key="step.title">
          <div class="decision-path__index" aria-hidden="true">{{ index + 1 }}</div>
          <PremiumIcon :name="step.icon" :size="25" :box-size="50" />
          <div class="decision-path__copy">
            <h3>{{ step.title }}</h3>
            <p>{{ step.description }}</p>
          </div>
          <span class="decision-path__evidence">{{ step.evidence }}</span>
        </li>
      </ol>
    </section>

    <section class="execution-section page-container" aria-labelledby="execution-title">
      <div class="execution-map">
        <div class="execution-map__copy">
          <h2 id="execution-title">计划不是终点，下一餐才是。</h2>
          <p>产品围绕“今日、计划、创建、我的”四个入口组织，让查看安排、回顾方案和更新画像都有清晰去处。</p>
          <el-button type="primary" size="large" @click="startUsing">开始建立计划</el-button>
        </div>
        <div class="execution-map__route" aria-label="产品使用流程">
          <div><b>今日</b><span>知道下一餐做什么</span></div>
          <i aria-hidden="true" />
          <div><b>计划</b><span>查看本周与营养依据</span></div>
          <i aria-hidden="true" />
          <div><b>采购</b><span>把食材一次买齐</span></div>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped lang="scss">
.hero { padding-top: clamp(18px, 3vw, 36px); }
.hero-shell {
  position: relative;
  display: grid;
  grid-template-columns: minmax(0, .9fr) minmax(520px, 1.1fr);
  min-height: 650px;
  align-items: center;
  gap: clamp(40px, 6vw, 86px);
  padding: clamp(42px, 6vw, 82px);
  border: 1px solid $color-border;
  border-top: 4px solid $color-accent;
  border-radius: $radius-xl;
  background: $color-surface;
  box-shadow: $shadow-xs;
}

.hero-copy { position: relative; z-index: 2; max-width: 590px; }
.hero h1 { color: $color-text-primary; font-size: $text-display; letter-spacing: -.065em; line-height: 1.02; }
.hero h1 span { display: block; white-space: nowrap; }
.hero-copy > p { max-width: 55ch; margin-top: $space-5; color: $color-text-secondary; font-size: clamp(16px, 1.4vw, 18px); line-height: 1.78; }
.hero-actions { display: flex; align-items: center; gap: $space-3; margin-top: $space-6; }
.hero-primary-action { border-color: $color-brand !important; background: $color-brand !important; box-shadow: none !important; color: $color-text-inverse !important; }
.hero-primary-action:hover { border-color: $color-brand-hover !important; background: $color-brand-hover !important; }
.hero-secondary-action {
  min-height: 50px;
  padding: 10px 16px;
  border: 1px solid rgba($color-brand, .32);
  border-radius: $radius-sm;
  background: transparent;
  color: $color-brand;
  cursor: pointer;
  font-weight: 720;
}
.hero-secondary-action:hover { border-color: $color-brand; background: rgba($color-surface, .52); color: $color-brand-hover; }
.trust-list { display: flex; flex-wrap: wrap; gap: 10px 18px; margin-top: $space-6; list-style: none; color: $color-text-secondary; font-size: 12px; }
.trust-list li { display: inline-flex; align-items: center; gap: 6px; }
.trust-list :deep(.premium-icon) { --icon-color: #{$color-brand}; --icon-bg: #{$color-accent}; border: 0; box-shadow: none; }

.plan-preview {
  position: relative;
  z-index: 2;
  min-width: 0;
  padding: clamp(18px, 2.4vw, 28px);
  border: 1px solid $color-border;
  border-radius: $radius-md;
  background: $color-background;
  box-shadow: $shadow-sm;
}
.plan-preview__header { display: flex; align-items: center; justify-content: space-between; gap: $space-4; }
.plan-preview__header > div { display: grid; }
.plan-preview__header span { color: $color-text-secondary; font-size: 12px; }
.plan-preview__header strong { font-size: $text-xl; letter-spacing: -.025em; }
.week-strip { display: grid; grid-template-columns: repeat(7, 1fr); gap: 5px; margin-top: $space-5; list-style: none; }
.week-strip li { display: grid; min-width: 0; justify-items: center; gap: 2px; padding: 10px 4px; border: 1px solid $color-divider; border-radius: $radius-sm; color: $color-text-secondary; }
.week-strip li.is-active { border-color: $color-brand; background: $color-brand; color: $color-text-inverse; }
.week-strip span { font-size: 11px; }
.week-strip strong { font-family: $font-numeric; font-size: 12px; font-variant-numeric: tabular-nums; }
.week-strip small { font-size: 8px; opacity: .74; }
.selected-day { margin-top: $space-4; padding: $space-4; border: 1px solid $color-divider; border-radius: $radius-md; background: $color-background; }
.selected-day__heading { display: flex; align-items: flex-end; justify-content: space-between; gap: $space-3; padding-bottom: $space-3; border-bottom: 1px solid $color-divider; }
.selected-day__heading > div { display: grid; }
.selected-day__heading span,
.selected-day__heading small { color: $color-text-secondary; font-size: 11px; }
.selected-day__heading strong { font-size: 17px; }
.meal-list { list-style: none; }
.meal-list li { display: grid; grid-template-columns: 8px 42px minmax(0, 1fr) auto; align-items: center; gap: 9px; min-height: 52px; border-bottom: 1px solid $color-divider; }
.meal-list li:last-child { border-bottom: 0; }
.meal-list > li > i { width: 8px; height: 26px; border-radius: $radius-round; }
.meal-list .tone-citrus { background: $color-accent-strong; }
.meal-list .tone-leaf { background: $leaf-600; }
.meal-list .tone-tomato { background: $tomato-500; }
.meal-list span { color: $color-text-secondary; font-size: 11px; }
.meal-list strong { min-width: 0; overflow: hidden; font-size: 13px; text-overflow: ellipsis; white-space: nowrap; }
.meal-list small { color: $color-text-secondary; font-family: $font-numeric; font-size: 10px; font-variant-numeric: tabular-nums; }
.plan-preview__footer { display: grid; grid-template-columns: repeat(3, 1fr); gap: $space-3; margin-top: $space-4; }
.plan-preview__footer > div { display: grid; padding-left: $space-3; border-left: 3px solid $color-accent-strong; }
.plan-preview__footer span,
.plan-preview__footer small { color: $color-text-secondary; font-size: 10px; }
.plan-preview__footer strong { color: $color-brand; font-family: $font-numeric; font-size: 17px; font-variant-numeric: tabular-nums; }

.goal-entry { display: grid; grid-template-columns: 260px 1fr; align-items: center; gap: $space-7; padding-top: $space-7; }
.goal-entry__heading h2 { font-size: $text-xl; letter-spacing: -.025em; }
.goal-options { display: grid; grid-template-columns: repeat(4, 1fr); gap: 0; border-block: 1px solid $color-border; }
.goal-options button { display: flex; min-width: 0; min-height: 68px; align-items: center; gap: 9px; padding: 10px 14px; border: 0; border-right: 1px solid $color-border; background: transparent; color: $color-text-primary; cursor: pointer; font-weight: 720; text-align: left; transition: background $motion-fast $ease-standard; }
.goal-options button:last-child { border-right: 0; }
.goal-options button:hover { background: $color-surface; }
.goal-options button :deep(.premium-icon) { border: 0; box-shadow: none; }

.decision-section { display: grid; grid-template-columns: minmax(280px, .72fr) minmax(0, 1.28fr); gap: clamp(48px, 8vw, 120px); padding-top: clamp(100px, 13vw, 170px); }
.decision-intro { align-self: start; position: sticky; top: 110px; }
.decision-intro h2 { max-width: 12ch; font-size: clamp(36px, 4.3vw, 58px); letter-spacing: -.055em; }
.decision-intro p { max-width: 48ch; margin-top: $space-5; color: $color-text-secondary; }
.inline-link { display: inline-flex; min-height: 44px; align-items: center; gap: 8px; margin-top: $space-5; border-bottom: 2px solid $color-accent-strong; font-weight: 760; }
.decision-path { list-style: none; border-top: 1px solid $color-border; }
.decision-path li { display: grid; grid-template-columns: 42px 50px minmax(0, 1fr); gap: $space-4; padding: clamp(28px, 5vw, 48px) 0; border-bottom: 1px solid $color-border; }
.decision-path__index { display: grid; width: 34px; height: 34px; place-items: center; border-radius: $radius-xs; background: $color-brand; color: $color-accent; font-family: $font-numeric; font-size: 12px; font-weight: 800; }
.decision-path li :deep(.premium-icon) { border: 0; box-shadow: none; }
.decision-path__copy h3 { font-size: clamp(21px, 2.2vw, 29px); letter-spacing: -.035em; }
.decision-path__copy p { max-width: 54ch; margin-top: $space-2; color: $color-text-secondary; font-size: 14px; }
.decision-path__evidence { grid-column: 3; justify-self: start; padding: 5px 10px; border-radius: $radius-round; background: $color-surface-accent; color: $color-brand; font-size: 11px; font-weight: 740; }

.execution-section { padding-top: clamp(96px, 12vw, 150px); }
.execution-map { display: grid; grid-template-columns: minmax(0, .82fr) minmax(460px, 1.18fr); align-items: center; gap: clamp(44px, 7vw, 100px); padding: clamp(38px, 6vw, 76px); border: 1px solid $color-border; border-top: 4px solid $color-accent; border-radius: $radius-lg; background: $color-surface; }
.execution-map__copy h2 { max-width: 12ch; font-size: clamp(34px, 4.2vw, 56px); letter-spacing: -.05em; }
.execution-map__copy p { max-width: 52ch; margin: $space-4 0 $space-5; color: $color-text-secondary; }
.execution-map__route { display: grid; grid-template-columns: 1fr 36px 1fr 36px 1fr; align-items: center; }
.execution-map__route > div { display: grid; min-height: 154px; align-content: center; gap: 6px; padding: $space-5; border: 1px solid $color-border; border-radius: $radius-sm; background: $color-surface-muted; text-align: center; }
.execution-map__route b { color: $color-brand; font-size: $text-xl; }
.execution-map__route span { color: $color-text-secondary; font-size: 12px; }
.execution-map__route > i { height: 2px; background: $color-brand; }

@media (max-width: 1100px) {
  .hero-shell { grid-template-columns: minmax(0, .82fr) minmax(460px, 1.18fr); padding: 52px 44px; }
  .goal-entry { grid-template-columns: 1fr; gap: $space-4; }
  .execution-map { grid-template-columns: 1fr; }
}

@media (max-width: 900px) {
  .hero-shell { grid-template-columns: 1fr; }
  .hero-copy { max-width: 680px; }
  .hero h1 { max-width: 12ch; }
  .plan-preview { width: min(100%, 620px); }
  .goal-options { grid-template-columns: repeat(2, 1fr); }
  .decision-section { grid-template-columns: 1fr; }
  .decision-intro { position: static; }
  .decision-intro h2 { max-width: 15ch; }
}

@media (max-width: $breakpoint-sm) {
  .hero { padding-top: 12px; }
  .hero-shell { min-height: auto; gap: $space-6; padding: 38px 20px 24px; border-radius: $radius-lg; }
  .hero h1 { font-size: clamp(42px, 13vw, 58px); }
  .hero-copy > p { font-size: 16px; }
  .hero-actions { align-items: stretch; flex-direction: column; }
  .hero-actions :deep(.el-button),
  .hero-secondary-action { width: 100%; margin: 0; }
  .trust-list { display: grid; }
  .plan-preview { padding: 16px 12px; border-radius: $radius-md; }
  .week-strip { gap: 3px; }
  .week-strip li { padding: 8px 2px; }
  .week-strip strong { font-size: 10px; }
  .selected-day { padding: 12px; }
  .meal-list li { grid-template-columns: 7px 34px minmax(0, 1fr); }
  .meal-list small { display: none; }
  .plan-preview__footer { gap: 5px; }
  .plan-preview__footer > div { padding-left: 7px; }
  .plan-preview__footer strong { font-size: 14px; }
  .goal-entry { padding-top: $space-6; }
  .goal-options { grid-template-columns: 1fr 1fr; }
  .goal-options button { min-height: 58px; padding: 8px; font-size: 12px; }
  .goal-options button:nth-child(2) { border-right: 0; }
  .goal-options button:nth-child(-n + 2) { border-bottom: 1px solid $color-border; }
  .goal-options button :deep(.premium-icon) { --icon-box-size: 34px; --icon-size: 17px; }
  .decision-section { padding-top: 88px; }
  .decision-intro h2 { font-size: 38px; }
  .decision-path li { grid-template-columns: 36px minmax(0, 1fr); gap: 12px; }
  .decision-path li :deep(.premium-icon) { display: none; }
  .decision-path__evidence { grid-column: 2; }
  .execution-section { padding-top: 80px; }
  .execution-map { min-width: 0; padding: 34px 20px; border-radius: $radius-lg; }
  .execution-map__route { grid-template-columns: 1fr; gap: 8px; }
  .execution-map__route > i { width: 2px; height: 22px; justify-self: center; }
  .execution-map__route > div { min-height: 120px; border-radius: $radius-lg; }
}
</style>
