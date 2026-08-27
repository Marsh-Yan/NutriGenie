<script setup lang="ts">
import { ref, watch } from 'vue'
import type { WeeklyDay } from '@/types'
import PremiumIcon from '@/components/common/PremiumIcon.vue'

const props = defineProps<{
  weeklyPlan: WeeklyDay[]
}>()

const dayNames = ['一', '二', '三', '四', '五', '六', '日']
const mealNames: Record<string, string> = { breakfast: '早餐', lunch: '午餐', dinner: '晚餐' }

const selectedDay = ref(0)

watch(() => props.weeklyPlan, (plan) => {
  if (!plan.length || selectedDay.value >= plan.length) selectedDay.value = 0
})

function scrollTo(idx: number) {
  selectedDay.value = idx
}
</script>

<template>
  <div class="weekly-timeline">
    <div class="section-heading">
      <h3 class="section-title"><PremiumIcon name="timeline" class="section-icon" :size="16" :box-size="32" />本周饮食规划</h3>
      <span class="section-context">点击日期查看三餐</span>
    </div>

    <!-- 日期导航 -->
    <div class="days-scroll" role="tablist" aria-label="一周饮食日期">
      <button
        v-for="(day, i) in weeklyPlan"
        :key="day.day"
        type="button"
        role="tab"
        class="day-btn"
        :class="{ active: selectedDay === i }"
        :aria-selected="selectedDay === i"
        @click="scrollTo(i)"
      >
        <span class="day-name">{{ dayNames[i] || day.day }}</span>
        <span class="day-cal">{{ (day.total_nutrition.calories || 0).toFixed(0) }}</span>
        <span class="day-unit">kcal</span>
      </button>
    </div>

    <!-- 选中日详情 -->
    <div v-if="weeklyPlan[selectedDay]" class="day-detail" role="tabpanel" aria-live="polite">
      <div
        v-for="(meal, slot) in weeklyPlan[selectedDay].meals"
        :key="slot"
        class="meal-row"
      >
        <div class="meal-label">{{ mealNames[slot] || slot }}</div>
        <div v-if="meal" class="meal-content">
          <span class="meal-name">
            {{ meal.name }}
            <small v-if="meal.serving_size > 1">× {{ meal.serving_size }} 份</small>
          </span>
          <span class="meal-cal">{{ meal.nutrition.calories.toFixed(0) }}kcal</span>
        </div>
        <div v-else class="meal-empty">—</div>
      </div>

      <div class="day-total">
        <span>当日总计</span>
        <span class="total-nutrition">
          {{ weeklyPlan[selectedDay].total_nutrition.calories.toFixed(0) }}kcal
          · P{{ (weeklyPlan[selectedDay].total_nutrition.protein_g || 0).toFixed(0) }}g
          · F{{ (weeklyPlan[selectedDay].total_nutrition.fat_g || 0).toFixed(0) }}g
          · C{{ (weeklyPlan[selectedDay].total_nutrition.carbs_g || 0).toFixed(0) }}g
        </span>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.weekly-timeline {
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
  color: $color-text-secondary;
  font-size: 12px;
  font-weight: 650;
}

// 日期导航

.days-scroll {
  display: flex;
  gap: 9px;
  overflow-x: auto;
  padding: 2px 2px 14px;
  scroll-snap-type: x proximity;
  scroll-behavior: smooth;

  &::-webkit-scrollbar { height: 4px; }
}

.day-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1px;
  min-width: 72px;
  min-height: 72px;
  padding: 10px 14px;
  border: 1px solid rgba($color-sage-dark, .12);
  border-radius: $radius-md;
  background: rgba($color-card, .92);
  box-shadow: $shadow-xs;
  cursor: pointer;
  scroll-snap-align: start;
  transition: border-color .2s ease, background-color .2s ease, box-shadow .2s ease, color .2s ease, transform .2s ease;

  &:hover {
    border-color: rgba($color-sage, .4);
    transform: translateY(-1px);
  }

  &.active {
    border-color: $color-sage-dark;
    background: linear-gradient(145deg, $color-sage, $color-sage-dark);
    box-shadow: 0 10px 22px rgba($color-sage-dark, .2);
    color: $color-text-inverse;
    transform: translateY(-2px);
  }
}

.day-name {
  font-size: 15px;
  font-weight: 600;
}

.day-cal {
  font-size: 14px;
  font-weight: 700;
}

.day-unit {
  font-size: 12px;
  font-weight: 600;
  opacity: .82;
}

// 日详情

.day-detail {
  position: relative;
  overflow: hidden;
  border: 1px solid rgba($color-sage-dark, .12);
  border-radius: $radius-lg;
  background: linear-gradient(145deg, rgba($color-card, .96), rgba($color-surface-soft, .66));
  box-shadow: $shadow-sm;
  padding: 18px;

  &::before {
    position: absolute;
    top: 0;
    bottom: 0;
    left: 0;
    width: 4px;
    background: linear-gradient($color-lime, $color-sage);
    content: '';
  }
}

.meal-row {
  display: flex;
  align-items: center;
  gap: 12px;
  min-height: 54px;
  padding: 10px 8px 10px 10px;

  & + & {
    border-top: 1px solid $color-divider;
  }
}

.meal-label {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 46px;
  min-height: 28px;
  border-radius: 999px;
  background: rgba($color-sage, .09);
  font-size: 12px;
  font-weight: 750;
  color: $color-sage-dark;
  flex-shrink: 0;
}

.meal-content {
  flex: 1;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.meal-name {
  font-size: 14px;
  font-weight: 650;
  color: $color-text-primary;
}

.meal-name small {
  margin-left: 4px;
  font-size: 12px;
  font-weight: 500;
  color: $color-text-secondary;
}

.meal-cal {
  padding: 4px 8px;
  border-radius: 999px;
  background: $color-surface-warm;
  font-size: 13px;
  color: $color-rose-dark;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

.meal-empty {
  color: $color-text-placeholder;
  font-size: 14px;
}

.day-total {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 12px;
  padding: 14px 8px 0 10px;
  border-top: 1px solid $color-divider;
  font-size: 13px;
  color: $color-text-secondary;
}

.total-nutrition {
  font-variant-numeric: tabular-nums;
  font-weight: 700;
  color: $color-text-primary;
}

@media (max-width: $breakpoint-sm) {
  .section-heading { align-items: flex-start; flex-direction: column; gap: 4px; }
  .days-scroll { margin-inline: -2px; }
  .day-btn { min-width: 68px; }
  .day-detail { padding: 12px; }
  .meal-row { align-items: flex-start; }
  .meal-content { align-items: flex-start; flex-direction: column; gap: 6px; }
  .meal-cal { padding: 0; background: transparent; font-size: 12px; }
  .day-total { align-items: flex-start; flex-direction: column; gap: 5px; }
  .total-nutrition { line-height: 1.6; }
}
</style>
