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

const macroItems = [
  { key: 'protein', label: '蛋白质', color: '#8FAA9B', pct: 'protein_pct' },
  { key: 'fat', label: '脂肪', color: '#D4B97A', pct: 'fat_pct' },
  { key: 'carbs', label: '碳水', color: '#C9A9A6', pct: 'carbs_pct' },
] as const
</script>

<template>
  <div class="nutrition-report">
    <h3 class="section-title"><PremiumIcon name="salad" class="section-icon" :size="16" :box-size="32" />营养概览</h3>

    <div class="report-grid">
      <div class="stat-card">
        <span class="stat-value">{{ report.avg_daily_calories.toFixed(0) }}</span>
        <span class="stat-label">日均热量 kcal</span>
      </div>
      <div class="stat-card">
        <span class="stat-value">{{ report.protein_g.toFixed(0) }}g</span>
        <span class="stat-label">日均蛋白质</span>
      </div>
      <div class="stat-card">
        <span class="stat-value">{{ report.fat_g.toFixed(0) }}g</span>
        <span class="stat-label">日均脂肪</span>
      </div>
      <div class="stat-card">
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
      <div class="calorie-bar-track">
        <div
          class="calorie-bar-fill"
          :style="{ width: `${calorieTarget ? Math.min(report.avg_daily_calories / calorieTarget * 100, 100) : 0}%` }"
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
            <span class="macro-pct">{{ (report[item.pct] * 100).toFixed(0) }}%</span>
          </div>
          <div class="macro-track">
            <div
              class="macro-fill"
              :style="{ width: `${report[item.pct] * 100}%`, background: item.color }"
            />
          </div>
        </div>
      </div>
    </div>

    <!-- 建议 -->
    <div v-if="report.recommendation" class="recommendation-box">
      <p class="recommendation-text">{{ report.recommendation }}</p>
    </div>
  </div>
</template>

<style scoped lang="scss">
.nutrition-report {
  margin-bottom: 32px;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 9px;
  font-size: 18px;
  font-weight: 600;
  color: $color-text-primary;
  margin-bottom: 16px;
}

.section-icon {
  border-radius: 10px;
  box-shadow: none;
}

// 统计卡片

.report-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
  margin-bottom: 20px;

  @media (max-width: $breakpoint-sm) {
    grid-template-columns: repeat(2, 1fr);
  }
}

.stat-card {
  text-align: center;
  padding: 16px 8px;
  background: rgba($color-sage, 0.05);
  border-radius: $radius-md;
}

.stat-value {
  display: block;
  font-size: 20px;
  font-weight: 700;
  color: $color-sage-dark;
}

.stat-label {
  display: block;
  font-size: 11px;
  color: $color-text-secondary;
  margin-top: 2px;
}

// 热量条

.calorie-bar-wrap {
  margin-bottom: 20px;
}

.calorie-bar-header {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  color: $color-text-secondary;
  margin-bottom: 6px;
}

.calorie-bar-track {
  height: 10px;
  background: $color-divider;
  border-radius: 5px;
  overflow: hidden;
}

.calorie-bar-fill {
  height: 100%;
  border-radius: 5px;
  background: linear-gradient(90deg, $color-sage, $color-rose);
  transition: width 0.6s ease;
}

// 宏量营养素

.macro-section {
  margin-bottom: 16px;
}

.macro-title {
  font-size: 14px;
  font-weight: 600;
  color: $color-text-primary;
  margin-bottom: 12px;
}

.macro-bars {
  display: flex;
  flex-direction: column;
  gap: 10px;
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
  height: 8px;
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
  background: rgba($color-sage, 0.06);
  border-radius: $radius-md;
  padding: 16px;
}

.recommendation-text {
  font-size: 14px;
  color: $color-text-primary;
  line-height: 1.7;
}
</style>
