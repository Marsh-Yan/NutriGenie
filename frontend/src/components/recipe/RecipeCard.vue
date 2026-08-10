<script setup lang="ts">
import { computed, ref } from 'vue'
import type { GeneratedRecipe, TopRecipe } from '@/types'
import { ArrowDown, ArrowUp } from '@element-plus/icons-vue'
import PremiumIcon from '@/components/common/PremiumIcon.vue'

const props = defineProps<{
  recipe: GeneratedRecipe | TopRecipe
  rank: number
}>()

const expanded = ref(false)

const categoryLabels: Record<string, string> = {
  main_dish: '主菜',
  side_dish: '配菜',
  soup: '汤',
  staple: '主食',
  light_meal: '轻食',
}

const isGenerated = computed(() => 'recipe_key' in props.recipe)
const generatedRecipe = computed(() => props.recipe as GeneratedRecipe)
const legacyRecipe = computed(() => props.recipe as TopRecipe)
const displayNutrition = computed(() => {
  if (isGenerated.value) return generatedRecipe.value.nutrition
  const nutrition = legacyRecipe.value.nutrition
  return {
    calories: nutrition.calories,
    protein_g: nutrition.protein,
    fat_g: nutrition.fat,
    carbs_g: nutrition.carbs,
    fiber_g: nutrition.fiber,
  }
})
const displayTime = computed(() => isGenerated.value
  ? generatedRecipe.value.prep_time_min + generatedRecipe.value.cook_time_min
  : legacyRecipe.value.prep_time + legacyRecipe.value.cook_time)
const displayNote = computed(() => isGenerated.value ? generatedRecipe.value.generation_note : legacyRecipe.value.explanation)
</script>

<template>
  <div class="recipe-card" :class="{ expanded }">
    <button class="card-main" type="button" :aria-expanded="expanded" @click="expanded = !expanded">
      <div class="rank-badge">{{ rank }}</div>

      <div class="card-info">
        <h3 class="recipe-name">{{ recipe.name }}</h3>
        <div class="recipe-tags">
          <el-tag size="small" round>{{ categoryLabels[recipe.category] || recipe.category }}</el-tag>
          <el-tag size="small" round type="info">{{ recipe.difficulty === 'easy' ? '简单' : recipe.difficulty === 'medium' ? '中等' : '困难' }}</el-tag>
          <span class="recipe-time">{{ displayTime }}min</span>
        </div>
      </div>

      <div class="card-cost">
        <span class="cost-value">¥{{ recipe.estimated_cost.toFixed(1) }}</span>
        <span class="cost-label">AI 估算成本</span>
      </div>

      <div class="card-expand">
        <el-icon>
          <component :is="expanded ? ArrowUp : ArrowDown" />
        </el-icon>
      </div>
    </button>

    <!-- 展开内容 -->
    <transition name="slide">
      <div v-show="expanded" class="card-detail">
        <div class="detail-section">
          <h4 class="detail-title"><PremiumIcon name="salad" class="detail-icon" :size="14" :box-size="28" />营养数据</h4>
          <div class="nutrition-grid">
            <div class="nut-item">
              <span class="nut-value">{{ displayNutrition.calories.toFixed(0) }}</span>
              <span class="nut-label">热量 kcal</span>
            </div>
            <div class="nut-item">
              <span class="nut-value">{{ displayNutrition.protein_g.toFixed(1) }}g</span>
              <span class="nut-label">蛋白质</span>
            </div>
            <div class="nut-item">
              <span class="nut-value">{{ displayNutrition.fat_g.toFixed(1) }}g</span>
              <span class="nut-label">脂肪</span>
            </div>
            <div class="nut-item">
              <span class="nut-value">{{ displayNutrition.carbs_g.toFixed(1) }}g</span>
              <span class="nut-label">碳水</span>
            </div>
          </div>
        </div>

        <div class="detail-section" v-if="isGenerated">
          <h4 class="detail-title"><PremiumIcon name="nutrition" class="detail-icon" :size="14" :box-size="28" />食材与步骤</h4>
          <div class="ingredient-list">
            <span v-for="ingredient in generatedRecipe.ingredients" :key="`${ingredient.name}-${ingredient.unit}`">
              {{ ingredient.name }} {{ ingredient.quantity }}{{ ingredient.unit }}
            </span>
          </div>
          <ol class="step-list">
            <li v-for="step in generatedRecipe.steps" :key="step">{{ step }}</li>
          </ol>
        </div>

        <div class="detail-section" v-if="displayNote">
          <h4 class="detail-title"><PremiumIcon name="plan" class="detail-icon" :size="14" :box-size="28" />AI 生成理由</h4>
          <p class="explanation-text">{{ displayNote }}</p>
        </div>
      </div>
    </transition>
  </div>
</template>

<style scoped lang="scss">
.recipe-card {
  background: $color-card;
  border: 1px solid $color-border;
  border-radius: $radius-lg;
  overflow: hidden;
  transition: all 0.3s;

  &:hover {
    box-shadow: $shadow-sm;
  }

  &.expanded {
    box-shadow: $shadow-md;
  }
}

.card-main {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px 20px;
  cursor: pointer;
  user-select: none;
  width: 100%;
  border: 0;
  background: transparent;
  color: inherit;
  font: inherit;
  text-align: left;

  @media (max-width: $breakpoint-sm) {
    flex-wrap: wrap;
  }
}

.rank-badge {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: linear-gradient(135deg, $color-sage, $color-sage-dark);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 700;
  flex-shrink: 0;
}

.card-info {
  flex: 1;
  min-width: 0;
}

.recipe-name {
  font-size: 16px;
  font-weight: 600;
  color: $color-text-primary;
  margin-bottom: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.recipe-tags {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
}

.recipe-time {
  color: $color-text-placeholder;
  font-size: 12px;
}

// ── 评分圆环 ─────────────────────────────

.card-score {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex-shrink: 0;
}

.score-ring {
  position: relative;
  width: 44px;
  height: 44px;
}

.score-svg {
  width: 100%;
  height: 100%;
}

.score-text {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 700;
  color: $color-text-primary;
}

.score-label {
  font-size: 10px;
  color: $color-text-placeholder;
  margin-top: 2px;
}

// ── 成本 ─────────────────────────────────

.card-cost {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex-shrink: 0;
}

.cost-value {
  font-size: 15px;
  font-weight: 700;
  color: $color-rose-dark;
}

.cost-label {
  font-size: 10px;
  color: $color-text-placeholder;
}

.card-expand {
  color: $color-text-placeholder;
  font-size: 16px;
  flex-shrink: 0;
  transition: transform 0.3s;

  .expanded & {
    transform: rotate(180deg);
  }
}

// ── 展开区 ───────────────────────────────

.slide-enter-active, .slide-leave-active {
  transition: all 0.25s ease;
}

.slide-enter-from, .slide-leave-to {
  opacity: 0;
  max-height: 0;
}

.card-detail {
  border-top: 1px solid $color-divider;
  padding: 20px;
}

.detail-section {
  margin-bottom: 20px;

  &:last-child {
    margin-bottom: 0;
  }
}

.detail-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 600;
  color: $color-text-primary;
  margin-bottom: 12px;
}

.detail-icon {
  border-radius: 9px;
  box-shadow: none;
}

// 营养网格

.nutrition-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
}

.nut-item {
  text-align: center;
  padding: 10px 8px;
  background: rgba($color-sage, 0.05);
  border-radius: $radius-sm;
}

.nut-value {
  display: block;
  font-size: 15px;
  font-weight: 700;
  color: $color-text-primary;
}

.nut-label {
  display: block;
  font-size: 11px;
  color: $color-text-secondary;
  margin-top: 2px;
}

// 评分条

.scores-grid {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.score-bar-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
}

.score-bar-label {
  width: 60px;
  font-size: 13px;
  color: $color-text-secondary;
  text-align: right;
  flex-shrink: 0;
}

.score-bar-track {
  flex: 1;
  height: 8px;
  background: $color-divider;
  border-radius: 4px;
  overflow: hidden;
}

.score-bar-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.6s ease;
}

.score-bar-value {
  width: 24px;
  text-align: right;
  font-size: 12px;
  font-weight: 600;
  color: $color-text-primary;
}

// 推荐理由

.explanation-text {
  font-size: 14px;
  color: $color-text-primary;
  line-height: 1.7;
}

.evidence-tags { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 8px; }
.evidence-text { font-size: 13px; color: $color-text-secondary; }
.evidence-warning { margin-top: 6px; font-size: 13px; color: $color-rose-dark; }
</style>
