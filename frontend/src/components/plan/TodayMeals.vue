<script setup lang="ts">
import type { WeeklyDay } from '@/types'
import type { MealExecutionStatus } from '@/types/localState'

defineProps<{
  day: WeeklyDay
  statusFor: (day: number, slot: string) => MealExecutionStatus
  statusDisabled?: boolean
}>()

const emit = defineEmits<{
  status: [day: number, slot: string, status: MealExecutionStatus]
  recipe: [recipeId: string]
}>()

const mealNames: Record<string, string> = { breakfast: '早餐', lunch: '午餐', dinner: '晚餐' }
const statusOptions: { value: MealExecutionStatus; label: string }[] = [
  { value: 'completed', label: '已完成' },
  { value: 'adjusted', label: '有调整' },
  { value: 'skipped', label: '跳过' },
]

function recipeId(meal: WeeklyDay['meals'][string]) {
  if (!meal) return ''
  return String(meal.recipe_key || meal.recipe_id || '')
}
</script>

<template>
  <section class="today-meals" aria-labelledby="today-meals-title">
    <header class="today-heading">
      <div>
        <span>第 {{ day.day }} 天</span>
        <h2 id="today-meals-title">今天的三餐</h2>
      </div>
      <strong>{{ day.total_nutrition.calories.toFixed(0) }} <small>kcal</small></strong>
    </header>

    <div class="meal-list">
      <article v-for="(meal, slot) in day.meals" :key="slot" class="meal-card">
        <div class="meal-copy">
          <span class="meal-slot">{{ mealNames[slot] || slot }}</span>
          <button
            v-if="meal && recipeId(meal)"
            type="button"
            class="meal-name meal-link"
            @click="emit('recipe', recipeId(meal))"
          >
            {{ meal.name }}
          </button>
          <strong v-else-if="meal" class="meal-name">{{ meal.name }}</strong>
          <span v-else class="meal-empty">本餐暂未安排</span>
          <small v-if="meal">{{ meal.nutrition.calories.toFixed(0) }} kcal · {{ meal.serving_size }} 份</small>
        </div>

        <div v-if="meal" class="execution-actions" :aria-label="`${mealNames[slot] || slot}执行状态`">
          <button
            v-for="option in statusOptions"
            :key="option.value"
            type="button"
            :class="{ active: statusFor(day.day, slot) === option.value }"
            :aria-pressed="statusFor(day.day, slot) === option.value"
            :disabled="statusDisabled"
            @click="emit('status', day.day, slot, statusFor(day.day, slot) === option.value ? 'pending' : option.value)"
          >
            {{ option.label }}
          </button>
        </div>
      </article>
    </div>
  </section>
</template>

<style scoped lang="scss">
.today-meals { display: grid; gap: 20px; }
.today-heading { display: flex; align-items: end; justify-content: space-between; gap: 20px; }
.today-heading div { display: grid; gap: 4px; }
.today-heading span { color: $color-sage-dark; font-size: 13px; font-weight: 800; }
.today-heading h2 { font-size: clamp(25px, 3vw, 34px); letter-spacing: -.04em; }
.today-heading > strong { color: $color-text-primary; font-size: 24px; font-variant-numeric: tabular-nums; }
.today-heading > strong small { color: $color-text-secondary; font-size: 12px; }
.meal-list { display: grid; gap: 12px; }
.meal-card {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: 20px;
  min-height: 112px;
  padding: 20px;
  border: 1px solid rgba($color-sage-dark, .12);
  border-radius: $radius-md;
  background: linear-gradient(135deg, rgba($color-card, .98), rgba($color-surface-soft, .68));
}
.meal-copy { display: grid; justify-items: start; gap: 5px; }
.meal-slot { padding: 4px 9px; border-radius: 999px; background: $color-lime-soft; color: $color-sage-dark; font-size: 12px; font-weight: 800; }
.meal-name { color: $color-text-primary; font-size: 18px; font-weight: 760; line-height: 1.4; }
.meal-link { padding: 0; border: 0; background: transparent; cursor: pointer; text-align: left; text-decoration: underline; text-decoration-color: rgba($color-sage, .32); text-underline-offset: 4px; }
.meal-link:hover { color: $color-sage-dark; text-decoration-color: currentColor; }
.meal-copy small, .meal-empty { color: $color-text-secondary; font-size: 13px; }
.execution-actions { display: flex; flex-wrap: wrap; justify-content: flex-end; gap: 7px; }
.execution-actions button {
  min-height: 44px;
  padding: 8px 12px;
  border: 1px solid $color-border;
  border-radius: $radius-round;
  background: $color-card;
  color: $color-text-secondary;
  cursor: pointer;
  font: inherit;
  font-size: 13px;
  font-weight: 700;
}
.execution-actions button:hover { border-color: rgba($color-sage, .5); color: $color-sage-dark; }
.execution-actions button.active { border-color: $color-sage-dark; background: $color-sage-dark; color: $color-text-inverse; }
.execution-actions button:disabled { cursor: not-allowed; opacity: .5; }

@media (max-width: $breakpoint-sm) {
  .meal-card { grid-template-columns: 1fr; gap: 14px; }
  .execution-actions { justify-content: flex-start; }
}
</style>
