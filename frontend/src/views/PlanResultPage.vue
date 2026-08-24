<script setup lang="ts">
import { computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { usePlanStore } from '@/stores/plan'
import RecipeCard from '@/components/recipe/RecipeCard.vue'
import WeeklyTimeline from '@/components/plan/WeeklyTimeline.vue'
import NutritionReport from '@/components/plan/NutritionReport.vue'
import ShoppingList from '@/components/plan/ShoppingList.vue'
import { Refresh } from '@element-plus/icons-vue'
import PremiumIcon from '@/components/common/PremiumIcon.vue'
import ProgressStepper from '@/components/plan/ProgressStepper.vue'

const route = useRoute()
const router = useRouter()
const store = usePlanStore()

const overview = computed(() => {
  const result = store.result
  if (!result) return null
  return {
    calories: result.nutrition_report.avg_daily_calories,
    cost: result.plan_validation?.estimated_procurement_cost,
    recipes: result.top5.length,
    warnings: result.plan_validation?.warnings.length || 0,
  }
})

onMounted(() => {
  const planId = Number(route.params.id)
  if (Number.isInteger(planId) && planId > 0) store.load(planId)
  else {
    store.status = 'failed'
    store.error = '方案编号无效，请从“我的方案”重新进入'
  }
})

onUnmounted(() => store.stopPolling())

watch(() => store.status, (status) => {
  if (status === 'completed' || status === 'failed') {
    store.stopPolling()
  }
})

function printPlan() {
  window.print()
}
</script>

<template>
  <div class="plan-result-page page-container">

    <!-- 加载/等待状态 -->
    <div v-if="store.status === 'pending' || store.status === 'running' || store.resultLoading" class="loading-section">
      <div class="loading-card card">
        <div class="loading-animation">
          <div class="loading-ring" />
          <PremiumIcon name="thinking" class="loading-icon" :size="34" :box-size="68" />
        </div>
        <h1 class="loading-title">{{ store.resultLoading ? '方案已生成，正在整理结果…' : 'AI 正在为你规划…' }}</h1>
        <p class="loading-desc">
          {{ store.status === 'pending' ? '等待中，即将开始' : '正在分析你的需求、匹配菜谱...' }}
        </p>
        <ProgressStepper :status="store.status" :progress="store.progress" />
      </div>
    </div>

    <!-- 失败状态 -->
    <div v-else-if="store.status === 'failed'" class="error-section">
      <div class="error-card card">
        <PremiumIcon name="alert" class="error-icon" :size="36" :box-size="72" />
        <h2 class="error-title">规划生成失败</h2>
        <p class="error-desc">{{ store.error || '请重试' }}</p>
        <el-button type="primary" round @click="$router.push('/plan/new')">
          <el-icon><Refresh /></el-icon>
          重新尝试
        </el-button>
        <el-button round @click="store.retry()">继续获取结果</el-button>
      </div>
    </div>

    <!-- 结果页面 -->
    <div v-else-if="store.result" class="result-section">
      <section v-if="overview" class="overview-card card" aria-labelledby="overview-title">
        <div class="overview-heading">
          <div><span class="eyebrow">你的专属方案</span><h1 id="overview-title">本周饮食概览</h1></div>
          <el-tag :type="overview.warnings ? 'warning' : 'success'" effect="light">
            {{ overview.warnings ? `${overview.warnings} 条提醒` : '整体匹配良好' }}
          </el-tag>
        </div>
        <div class="overview-grid">
          <div><strong>{{ overview.calories.toFixed(0) }}</strong><span>日均 kcal</span></div>
          <div><strong>{{ overview.cost == null ? '—' : `¥${overview.cost.toFixed(0)}` }}</strong><span>预计采购</span></div>
          <div><strong>{{ overview.recipes }}</strong><span>精选菜谱</span></div>
        </div>
        <div class="result-actions">
          <el-button round @click="printPlan">打印方案</el-button>
          <el-button type="primary" round @click="router.push('/plan/new')">重新规划</el-button>
        </div>
      </section>
      <section v-if="store.result.recommendation_meta" class="recommendation-status card">
        <details>
          <summary>查看推荐依据</summary>
          <p>方案由饮食约束、营养目标与语义检索共同生成。</p>
          <el-tag :type="store.result.recommendation_meta.fallback_used ? 'warning' : 'success'" effect="light">
            {{ store.result.recommendation_meta.fallback_used ? '当前使用基础推荐模式' : '已结合知识库匹配' }}
          </el-tag>
        </details>
      </section>
      <!-- TOP5 -->
      <section class="result-block">
        <h2 class="block-title">
          <PremiumIcon name="trophy" class="heading-icon" :size="18" :box-size="34" />
          TOP5 推荐菜谱
          <span class="block-subtitle">按综合评分排序</span>
        </h2>
        <div class="top5-list">
          <RecipeCard
            v-for="(recipe, i) in store.result.top5"
            :key="recipe.recipe_id"
            :recipe="recipe"
            :rank="i + 1"
          />
        </div>
      </section>

      <!-- 周计划 -->
      <section v-if="store.result.weekly_plan.length > 0" class="result-block">
        <WeeklyTimeline :weekly-plan="store.result.weekly_plan" />
      </section>

      <section v-if="store.result.plan_validation" class="result-block">
        <div class="validation-card card" :class="{ warning: store.result.plan_validation.warnings.length }">
          <h3 class="validation-heading"><PremiumIcon name="check" :size="13" :box-size="26" />计划校验</h3>
          <p>日均 {{ store.result.plan_validation.avg_daily_calories.toFixed(0) }} kcal，目标 {{ store.result.plan_validation.target_calorie_range.join(' - ') }} kcal</p>
          <p v-if="store.result.plan_validation.budget_target_range">采购 ¥{{ (store.result.plan_validation.estimated_procurement_cost || 0).toFixed(1) }}，目标 ¥{{ store.result.plan_validation.budget_target_range.join(' - ') }}</p>
          <p v-for="warning in store.result.plan_validation.warnings" :key="warning" class="validation-warning">
            <PremiumIcon name="alert" :size="12" :box-size="24" />{{ warning }}
          </p>
          <p v-if="!store.result.plan_validation.warnings.length" class="validation-ok">计划完整，未发现需要提示的偏差。</p>
        </div>
      </section>

      <!-- 营养报告 -->
      <section class="result-block">
        <NutritionReport
          :report="store.result.nutrition_report"
          :target-range="store.result.plan_validation?.target_calorie_range"
        />
      </section>

      <!-- 采购清单 -->
      <section class="result-block">
        <ShoppingList :shopping-list="store.result.shopping_list" />
      </section>

      <!-- AI 总结 -->
      <section v-if="store.result.summary" class="result-block">
        <div class="summary-card card">
          <h3 class="summary-title">
            <PremiumIcon name="clipboard" class="heading-icon" :size="17" :box-size="32" />
            AI 总结
          </h3>
          <div class="summary-content">{{ store.result.summary }}</div>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped lang="scss">
.plan-result-page {
  padding: 32px 20px;
  max-width: 800px;
}

// ── 加载状态 ─────────────────────────────

.loading-section {
  padding-top: 40px;
}

.loading-card {
  text-align: center;
  padding: 60px 40px;
}

.loading-animation {
  position: relative;
  width: 80px;
  height: 80px;
  margin: 0 auto 24px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.loading-ring {
  position: absolute;
  inset: 0;
  border: 3px solid $color-divider;
  border-top-color: $color-sage;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.loading-icon {
  position: relative;
  z-index: 1;
}

.loading-title {
  font-size: 20px;
  font-weight: 600;
  color: $color-text-primary;
  margin-bottom: 8px;
}

.loading-desc {
  font-size: 14px;
  color: $color-text-secondary;
}

.loading-card :deep(.progress-stepper) { margin: 32px auto 0; max-width: 640px; text-align: left; }

// ── 错误状态 ─────────────────────────────

.error-section {
  padding-top: 60px;
}

.error-card {
  text-align: center;
  padding: 60px 40px;
}

.error-icon {
  display: inline-grid;
  margin-bottom: 16px;
}

.error-title {
  font-size: 20px;
  font-weight: 600;
  color: $color-text-primary;
  margin-bottom: 8px;
}

.error-desc {
  font-size: 14px;
  color: $color-text-secondary;
  margin-bottom: 24px;
}

// ── 结果状态 ─────────────────────────────

.result-section {
  padding-top: 8px;
}

.overview-card { margin-bottom: 24px; padding: 28px; background: linear-gradient(135deg, rgba($color-sage,.14), rgba($color-rose,.09)); }
.overview-heading { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; }
.overview-heading h1 { margin-top: 4px; color: $color-text-primary; font-size: 26px; }
.eyebrow { color: $color-sage-dark; font-size: 13px; font-weight: 700; letter-spacing: .08em; }
.overview-grid { display: grid; grid-template-columns: repeat(3,1fr); gap: 12px; margin-top: 22px; }
.overview-grid div { display: flex; flex-direction: column; padding: 14px; border-radius: $radius-md; background: rgba(255,255,255,.72); }
.overview-grid strong { color: $color-text-primary; font-size: 22px; }
.overview-grid span { color: $color-text-secondary; font-size: 12px; }
.result-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 18px; }

.result-block {
  margin-bottom: 40px;
}

.block-title {
  font-size: 20px;
  font-weight: 700;
  color: $color-text-primary;
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.block-subtitle {
  font-size: 13px;
  font-weight: 400;
  color: $color-text-secondary;
}

.top5-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.recommendation-status { padding: 14px 18px; margin-bottom: 24px; }
.recommendation-status summary { color: $color-text-primary; cursor: pointer; font-weight: 600; }
.recommendation-status p { margin: 10px 0; color: $color-text-secondary; font-size: 13px; }
.validation-card { padding: 20px; }
.validation-heading { display: flex; align-items: center; gap: 8px; }
.validation-heading .premium-icon,
.validation-warning .premium-icon { border-radius: 8px; box-shadow: none; vertical-align: -7px; }
.validation-card h3 { margin-bottom: 8px; color: $color-text-primary; font-size: 17px; }
.validation-card p { margin-top: 6px; font-size: 14px; color: $color-text-secondary; line-height: 1.6; }
.validation-card.warning { border-color: $color-rose; }
.validation-ok { color: $color-sage-dark !important; }
.validation-warning { display: flex; align-items: center; gap: 8px; }

// ── 总结 ─────────────────────────────────

.summary-card {
  padding: 24px;
}

.summary-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 18px;
  font-weight: 600;
  color: $color-text-primary;
  margin-bottom: 12px;
}

.summary-content {
  font-size: 14px;
  color: $color-text-primary;
  line-height: 1.8;
  white-space: pre-wrap;
}

@media (max-width: $breakpoint-sm) {
  .plan-result-page { padding-top: 24px; }
  .overview-card { padding: 20px; }
  .overview-heading { flex-direction: column; }
  .overview-grid { gap: 8px; }
  .overview-grid div { padding: 12px 8px; }
  .overview-grid strong { font-size: 18px; }
}

@media print {
  .result-actions, :global(.app-header), :global(.mobile-nav), :global(.app-footer) { display: none !important; }
  .plan-result-page { max-width: none; padding: 0; }
  .card { break-inside: avoid; box-shadow: none; }
}
</style>
