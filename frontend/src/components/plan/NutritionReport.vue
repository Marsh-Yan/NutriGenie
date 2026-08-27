<script setup lang="ts">
import { computed } from 'vue'
import type { NutritionReport as NutritionReportType } from '@/types'
import PremiumIcon from '@/components/common/PremiumIcon.vue'

const props = defineProps<{
  report: NutritionReportType
  targetRange?: number[]
}>()

const calorieTarget = computed(() => {
  if (!props.targetRange || props.targetRange.length < 2) return null
  return (props.targetRange[0] + props.targetRange[1]) / 2
})
const calorieTargetLabel = computed(() => props.targetRange?.length === 2
  ? `${props.targetRange[0].toFixed(0)}–${props.targetRange[1].toFixed(0)} kcal`
  : '未设置')
const calorieProgress = computed(() => calorieTarget.value
  ? Math.min(100, Math.max(0, reportValue(props.report.avg_daily_calories / calorieTarget.value * 100)))
  : 0)

const reportValue = (value: number) => Number.isFinite(value) ? value : 0
const asPercent = (value: number) => Math.min(100, Math.max(0, reportValue(value * 100)))

const macroItems = [
  { key: 'protein', label: '蛋白质', color: '#F06B5B', pct: 'protein_pct' },
  { key: 'fat', label: '脂肪', color: '#7F7AEF', pct: 'fat_pct' },
  { key: 'carbs', label: '碳水', color: '#E8B344', pct: 'carbs_pct' },
] as const
</script>

<template>
  <div class="nutrition-report">
    <div class="section-heading">
      <h3 class="section-title"><PremiumIcon name="salad" class="section-icon" :size="16" :box-size="32" />营养概览</h3>
      <span class="section-context">每日平均</span>
    </div>

    <div class="report-grid">
      <div class="stat-card stat-card--calories">
        <span class="stat-value">{{ report.avg_daily_calories.toFixed(0) }}</span>
        <span class="stat-label">日均热量 kcal</span>
      </div>
      <div class="stat-card stat-card--protein">
        <span class="stat-value">{{ report.protein_g.toFixed(0) }}g</span>
        <span class="stat-label">日均蛋白质</span>
      </div>
      <div class="stat-card stat-card--fat">
        <span class="stat-value">{{ report.fat_g.toFixed(0) }}g</span>
        <span class="stat-label">日均脂肪</span>
      </div>
      <div class="stat-card stat-card--carbs">
        <span class="stat-value">{{ report.carbs_g.toFixed(0) }}g</span>
        <span class="stat-label">日均碳水</span>
      </div>
    </div>

    <!-- 热量进度条 -->
    <div class="calorie-bar-wrap">
      <div class="calorie-bar-header">
        <span>热量摄入</span>
        <span>{{ report.avg_daily_calories.toFixed(0) }} / {{ calorieTargetLabel }}</span>
      </div>
      <div
        class="calorie-bar-track"
        role="progressbar"
        aria-label="日均热量目标完成度"
        :aria-valuenow="Math.round(calorieProgress)"
        aria-valuemin="0"
        aria-valuemax="100"
      >
        <div
          class="calorie-bar-fill"
          :style="{ width: `${calorieProgress}%` }"
        />
      </div>
    </div>

    <!-- 宏量营养素占比 -->
    <div class="macro-section">
      <h4 class="macro-title">宏量营养素分布</h4>
      <div class="macro-bars">
        <div v-for="item in macroItems" :key="item.key" class="macro-item">
          <div class="macro-header">
            <span class="macro-dot" :style="{ background: item.color }" />
            <span class="macro-label">{{ item.label }}</span>
            <span class="macro-pct">{{ asPercent(report[item.pct]).toFixed(0) }}%</span>
          </div>
          <div
            class="macro-track"
            role="progressbar"
            :aria-label="`${item.label}占比`"
            :aria-valuenow="Math.round(asPercent(report[item.pct]))"
            aria-valuemin="0"
            aria-valuemax="100"
          >
            <div
              class="macro-fill"
              :style="{ width: `${asPercent(report[item.pct])}%`, background: item.color }"
            />
          </div>
        </div>
      </div>
    </div>

    <!-- 建议 -->
    <div v-if="report.recommendation" class="recommendation-box">
      <PremiumIcon name="thinking" class="recommendation-icon" :size="15" :box-size="30" />
      <div>
        <strong>营养师建议</strong>
        <p class="recommendation-text">{{ report.recommendation }}</p>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.nutrition-report {
  width: 100%;
}

.section-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 9px;
  margin: 0;
  color: $color-text-primary;
  font-size: 19px;
  font-weight: 750;
}

.section-icon {
  border-radius: 10px;
  box-shadow: none;
}

.section-context {
  padding: 5px 10px;
  border-radius: 999px;
  background: $color-surface-soft;
  color: $color-text-secondary;
  font-size: 12px;
  font-weight: 700;
}

// 统计卡片

.report-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
  margin-bottom: 24px;

  @media (max-width: $breakpoint-sm) {
    grid-template-columns: repeat(2, 1fr);
  }
}

.stat-card {
  position: relative;
  min-width: 0;
  overflow: hidden;
  padding: 16px 12px;
  border: 1px solid rgba($color-sage-dark, .08);
  border-radius: $radius-md;
  background: $color-surface-soft;

  &::before {
    position: absolute;
    top: 0;
    right: 0;
    left: 0;
    height: 3px;
    background: $color-sage;
    content: '';
  }

  &--protein { background: rgba($score-utilization, .07); &::before { background: $score-utilization; } }
  &--fat { background: rgba($score-preference, .07); &::before { background: $score-preference; } }
  &--carbs { background: rgba($score-season, .09); &::before { background: $score-season; } }
}

.stat-value {
  display: block;
  font-size: 20px;
  font-variant-numeric: tabular-nums;
  font-weight: 800;
  color: $color-text-primary;
}

.stat-label {
  display: block;
  font-size: 13px;
  font-weight: 600;
  color: $color-text-secondary;
  margin-top: 2px;
}

// 热量条

.calorie-bar-wrap {
  margin-bottom: 24px;
  padding: 14px 16px;
  border: 1px solid rgba($color-sage-dark, .08);
  border-radius: $radius-md;
  background: rgba($color-card, .7);
}

.calorie-bar-header {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  color: $color-text-secondary;
  gap: 16px;
  margin-bottom: 9px;
}

.calorie-bar-track {
  height: 9px;
  background: rgba($color-sage, .12);
  border-radius: 999px;
  overflow: hidden;
}

.calorie-bar-fill {
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, $color-sage-dark, $color-sage 68%, $color-lime);
  box-shadow: 0 0 14px rgba($color-sage, .2);
  transition: width 0.6s ease;
}

// 宏量营养素

.macro-section {
  margin-bottom: 20px;
}

.macro-title {
  font-size: 14px;
  font-weight: 750;
  color: $color-text-primary;
  margin-bottom: 12px;
}

.macro-bars {
  display: grid;
  gap: 12px;
}

.macro-item {
  padding: 11px 12px;
  border: 1px solid rgba($color-sage-dark, .07);
  border-radius: $radius-sm;
  background: rgba($color-card, .72);
}

.macro-header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 4px;
}

.macro-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.macro-label {
  font-size: 13px;
  color: $color-text-secondary;
}

.macro-pct {
  margin-left: auto;
  font-size: 13px;
  font-weight: 600;
  color: $color-text-primary;
}

.macro-track {
  height: 7px;
  background: $color-divider;
  border-radius: 4px;
  overflow: hidden;
}

.macro-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.6s ease;
}

// 建议

.recommendation-box {
  display: flex;
  align-items: flex-start;
  gap: 11px;
  border: 1px solid rgba($color-sage, .15);
  border-radius: $radius-md;
  background: linear-gradient(135deg, rgba($color-sage-light, .52), rgba($color-lime-soft, .46));
  padding: 16px;

  strong {
    display: block;
    margin-bottom: 3px;
    color: $color-sage-dark;
    font-size: 12px;
  }
}

.recommendation-icon { border-radius: 10px; box-shadow: none; }

.recommendation-text {
  font-size: 14px;
  color: $color-text-secondary;
  line-height: 1.7;
}

@media (max-width: 420px) {
  .report-grid { gap: 8px; }
  .stat-card { padding: 13px 10px; }
  .stat-value { font-size: 18px; }
  .calorie-bar-header { align-items: flex-start; flex-direction: column; gap: 2px; }
}
</style>
