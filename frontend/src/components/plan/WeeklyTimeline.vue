<script setup lang="ts">
import { ref } from 'vue'
import type { WeeklyDay } from '@/types'
import PremiumIcon from '@/components/common/PremiumIcon.vue'

const props = defineProps<{
  weeklyPlan: WeeklyDay[]
}>()

const dayNames = ['一', '二', '三', '四', '五', '六', '日']
const mealNames: Record<string, string> = { breakfast: '早餐', lunch: '午餐', dinner: '晚餐' }

const selectedDay = ref(0)

function scrollTo(idx: number) {
  selectedDay.value = idx
}
</script>

<template>
  <div class="weekly-timeline">
    <h3 class="section-title"><PremiumIcon name="timeline" class="section-icon" :size="16" :box-size="32" />本周饮食规划</h3>

    <!-- 日期导航 -->
    <div class="days-scroll">
      <button
        v-for="(day, i) in weeklyPlan"
        :key="day.day"
        class="day-btn"
        :class="{ active: selectedDay === i }"
        @click="scrollTo(i)"
      >
        <span class="day-name">{{ dayNames[i] || day.day }}</span>
        <span class="day-cal">{{ (day.total_nutrition.calories || 0).toFixed(0) }}</span>
        <span class="day-unit">kcal</span>
      </button>
    </div>

    <!-- 选中日详情 -->
    <div v-if="weeklyPlan[selectedDay]" class="day-detail">
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
          · P{{ weeklyPlan[selectedDay].total_nutrition.protein.toFixed(0) }}g
        </span>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.weekly-timeline {
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

// 日期导航

.days-scroll {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  padding-bottom: 12px;
  scroll-behavior: smooth;

  &::-webkit-scrollbar { height: 4px; }
}

.day-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  padding: 10px 16px;
  min-width: 64px;
  border: 1px solid $color-border;
  border-radius: $radius-md;
  background: $color-card;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    border-color: $color-sage-light;
  }

  &.active {
    background: $color-sage;
    border-color: $color-sage;
    color: #fff;
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
  font-size: 10px;
  opacity: 0.7;
}

// 日详情

.day-detail {
  background: $color-card;
  border: 1px solid $color-border;
  border-radius: $radius-lg;
  padding: 16px;
}

.meal-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 0;

  & + & {
    border-top: 1px solid $color-divider;
  }
}

.meal-label {
  width: 40px;
  font-size: 13px;
  font-weight: 600;
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
  font-weight: 500;
  color: $color-text-primary;
}

.meal-name small {
  margin-left: 4px;
  font-size: 12px;
  font-weight: 500;
  color: $color-text-secondary;
}

.meal-cal {
  font-size: 13px;
  color: $color-text-secondary;
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
  padding-top: 12px;
  border-top: 1px solid $color-divider;
  font-size: 13px;
  color: $color-text-secondary;
}

.total-nutrition {
  font-weight: 600;
  color: $color-text-primary;
}
</style>
