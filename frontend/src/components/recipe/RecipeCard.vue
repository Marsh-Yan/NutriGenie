<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { GeneratedRecipe, RecipeDetail, TopRecipe } from '@/types'
import { ArrowDown } from '@element-plus/icons-vue'
import PremiumIcon from '@/components/common/PremiumIcon.vue'
import { getRecipeDetail } from '@/api/recipes'

const props = withDefaults(defineProps<{
  recipe: GeneratedRecipe | TopRecipe
  rank: number
  enableDetail?: boolean
}>(), { enableDetail: true })

const expanded = ref(false)
const detail = ref<RecipeDetail | null>(null)
const detailLoading = ref(false)
const detailError = ref('')
const imageFailed = ref(false)

async function toggleExpanded() {
  expanded.value = !expanded.value
  if (!expanded.value || !props.enableDetail || isGenerated.value || detail.value || detailLoading.value) return
  detailLoading.value = true
  detailError.value = ''
  try {
    detail.value = await getRecipeDetail(legacyRecipe.value.recipe_id)
  } catch (e: unknown) {
    detailError.value = e instanceof Error ? e.message : '做法加载失败'
  } finally {
    detailLoading.value = false
  }
}

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
const displayImage = computed(() => isGenerated.value ? null : legacyRecipe.value.image_url)
const fallbackVariant = computed(() => `variant-${(props.rank - 1) % 3 + 1}`)

watch(displayImage, () => {
  imageFailed.value = false
})
</script>

<template>
  <div class="recipe-card" :class="{ expanded }">
    <button
      class="card-main"
      type="button"
      :aria-expanded="expanded"
      :aria-label="`${expanded ? '收起' : '展开'}${recipe.name}详情`"
      @click="toggleExpanded"
    >
      <div class="recipe-visual" :class="fallbackVariant">
        <img
          v-if="displayImage && !imageFailed"
          class="recipe-image"
          :src="displayImage"
          alt=""
          width="108"
          height="81"
          loading="lazy"
          decoding="async"
          @error="imageFailed = true"
        />
        <div v-else class="recipe-fallback" aria-hidden="true">
          <span class="fallback-orbit fallback-orbit--one" />
          <span class="fallback-orbit fallback-orbit--two" />
          <PremiumIcon name="salad" class="fallback-icon" :size="27" :box-size="54" />
        </div>
        <div class="rank-badge"><span>TOP</span>{{ rank }}</div>
      </div>

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
        <span class="cost-label">{{ isGenerated && generatedRecipe.estimate_source === 'ingredient_catalog_v1' ? '目录核算成本' : '预估成本' }}</span>
      </div>

      <div class="card-expand">
        <el-icon>
          <ArrowDown />
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

        <div v-if="enableDetail && !isGenerated" class="detail-section recipe-method">
          <h4 class="detail-title"><PremiumIcon name="clipboard" class="detail-icon" :size="14" :box-size="28" />食材与做法</h4>
          <p v-if="detailLoading" class="detail-message" aria-live="polite">正在加载完整做法…</p>
          <p v-else-if="detailError" class="detail-message error" role="alert">{{ detailError }}</p>
          <template v-else-if="detail">
            <ul class="ingredient-list">
              <li v-for="item in detail.ingredients" :key="item.ingredient_id">
                <span>{{ item.name }}</span><span>{{ item.quantity }} {{ item.unit }}</span>
              </li>
            </ul>
            <ol class="step-list">
              <li v-for="item in detail.steps" :key="item.step">{{ item.content }}</li>
            </ol>
          </template>
        </div>
      </div>
    </transition>
  </div>
</template>

<style scoped lang="scss">
.recipe-card {
  position: relative;
  border: 1px solid rgba($color-sage-dark, .12);
  border-radius: $radius-lg;
  background: rgba($color-card, .96);
  box-shadow: $shadow-xs;
  overflow: hidden;
  transition: border-color .25s ease, box-shadow .25s ease, transform .25s ease;

  &:hover {
    border-color: rgba($color-sage, .28);
    box-shadow: $shadow-sm;
    transform: translateY(-1px);
  }

  &.expanded {
    border-color: rgba($color-sage, .32);
    box-shadow: $shadow-md;
    transform: none;
  }
}

.card-main {
  display: grid;
  grid-template-areas: 'visual info cost expand';
  grid-template-columns: 108px minmax(0, 1fr) auto 34px;
  align-items: center;
  width: 100%;
  min-height: 112px;
  gap: 18px;
  padding: 14px 16px 14px 14px;
  border: 0;
  background: transparent;
  color: inherit;
  cursor: pointer;
  font: inherit;
  text-align: left;
  user-select: none;

  @media (max-width: $breakpoint-sm) {
    grid-template-areas:
      'visual info expand'
      'visual cost expand';
    grid-template-columns: 80px minmax(0, 1fr) 32px;
    gap: 8px 12px;
    min-height: 108px;
    padding: 12px;
  }
}

.recipe-visual {
  position: relative;
  grid-area: visual;
  width: 108px;
  aspect-ratio: 4 / 3;
  overflow: hidden;
  border: 1px solid rgba($color-sage-dark, .08);
  border-radius: $radius-md;
  background: $color-surface-soft;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, .76);

  @media (max-width: $breakpoint-sm) {
    width: 80px;
    height: 84px;
    aspect-ratio: auto;
  }
}

.recipe-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform .35s ease;

  .recipe-card:hover & { transform: scale(1.035); }
}

.recipe-fallback {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  overflow: hidden;
  background:
    radial-gradient(circle at 72% 24%, rgba($color-lime, .48), transparent 24%),
    linear-gradient(145deg, $color-sage-light, $color-surface-soft);
}

.recipe-visual.variant-2 .recipe-fallback {
  background:
    radial-gradient(circle at 72% 24%, rgba($color-butter, .46), transparent 24%),
    linear-gradient(145deg, $color-surface-warm, $color-rose-light);
}

.recipe-visual.variant-3 .recipe-fallback {
  background:
    radial-gradient(circle at 72% 24%, rgba($color-blue, .34), transparent 24%),
    linear-gradient(145deg, $color-blue-soft, $color-surface-soft);
}

.fallback-orbit {
  position: absolute;
  border: 1px solid rgba($color-card, .72);
  border-radius: 50%;

  &--one {
    right: -18px;
    bottom: -25px;
    width: 76px;
    height: 76px;
  }

  &--two {
    top: -19px;
    left: -12px;
    width: 52px;
    height: 52px;
  }
}

.fallback-icon {
  border-color: rgba($color-card, .68);
  border-radius: 17px;
  background: rgba($color-card, .72);
  box-shadow: 0 12px 26px rgba($color-sage-dark, .12);
  backdrop-filter: blur(6px);
}

.rank-badge {
  position: absolute;
  top: 7px;
  left: 7px;
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  border: 1px solid rgba(255, 255, 255, .5);
  border-radius: 11px;
  background: rgba($color-sage-dark, .9);
  box-shadow: 0 6px 14px rgba($color-sage-dark, .18);
  color: $color-text-inverse;
  font-size: 12px;
  font-variant-numeric: tabular-nums;
  font-weight: 800;
  line-height: 1;

  span {
    margin-bottom: -4px;
    font-size: 6px;
    letter-spacing: .08em;
  }
}

.card-info {
  grid-area: info;
  flex: 1;
  min-width: 0;
}

.recipe-name {
  display: -webkit-box;
  margin-bottom: 8px;
  overflow: hidden;
  color: $color-text-primary;
  font-size: 17px;
  font-weight: 750;
  line-height: 1.35;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.recipe-tags {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  font-size: 12px;

  :deep(.el-tag) {
    height: 24px;
    padding-inline: 9px;
    border-color: rgba($color-sage, .2);
    background: rgba($color-sage, .08);
    color: $color-sage-dark;
  }

  :deep(.el-tag--info) {
    border-color: rgba($color-blue, .22);
    background: $color-blue-soft;
    color: $color-info;
  }
}

.recipe-time {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: $color-text-placeholder;
  font-size: 12px;

  &::before {
    width: 4px;
    height: 4px;
    border-radius: 50%;
    background: $color-sage;
    content: '';
  }
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
  font-size: 12px;
  font-weight: 600;
  color: $color-text-placeholder;
  margin-top: 2px;
}

// ── 成本 ─────────────────────────────────

.card-cost {
  grid-area: cost;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  flex-shrink: 0;
  min-width: 94px;
  padding: 8px 10px;
  border: 1px solid rgba($color-rose, .16);
  border-radius: $radius-sm;
  background: $color-surface-warm;
}

.cost-value {
  font-size: 16px;
  font-variant-numeric: tabular-nums;
  font-weight: 800;
  color: $color-rose-dark;
}

.cost-label {
  font-size: 12px;
  font-weight: 600;
  color: $color-text-placeholder;
}

.card-expand {
  grid-area: expand;
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  border: 1px solid $color-divider;
  border-radius: 50%;
  background: $color-card;
  color: $color-text-placeholder;
  font-size: 16px;
  flex-shrink: 0;
  transition: border-color .25s ease, color .25s ease, transform .25s ease;

  .expanded & {
    transform: rotate(180deg);
    border-color: rgba($color-sage, .28);
    color: $color-sage-dark;
  }
}

// ── 展开区 ───────────────────────────────

.slide-enter-active,
.slide-leave-active {
  max-height: 1600px;
  overflow: hidden;
  transition: max-height .3s ease, opacity .24s ease;
}

.slide-enter-from,
.slide-leave-to {
  opacity: 0;
  max-height: 0;
}

.card-detail {
  border-top: 1px solid $color-divider;
  padding: 20px 24px 24px;
  background: linear-gradient(180deg, rgba($color-surface-soft, .72), rgba($color-card, .92));
}

.detail-section {
  padding: 16px;
  border: 1px solid rgba($color-sage-dark, .09);
  border-radius: $radius-md;
  background: rgba($color-card, .88);

  & + & { margin-top: 12px; }
}

.detail-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 750;
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
  padding: 12px 8px;
  border: 1px solid rgba($color-sage-dark, .08);
  background: $color-surface-soft;
  border-radius: $radius-sm;

  &:nth-child(2) { background: rgba($score-health, .1); }
  &:nth-child(3) { background: rgba($score-preference, .1); }
  &:nth-child(4) { background: rgba($score-season, .12); }
}

.nut-value {
  display: block;
  font-size: 15px;
  font-weight: 700;
  color: $color-text-primary;
}

.nut-label {
  display: block;
  font-size: 12px;
  font-weight: 600;
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
  color: $color-text-secondary;
  line-height: 1.7;
}

.evidence-tags { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 8px; }
.evidence-text { font-size: 13px; color: $color-text-secondary; }
.evidence-warning { margin-top: 6px; font-size: 13px; color: $color-rose-dark; }
.detail-message { color: $color-text-secondary; font-size: 13px; }
.detail-message.error { color: $color-danger; }
.ingredient-list, .step-list { display: grid; gap: 7px; color: $color-text-primary; font-size: 13px; line-height: 1.6; }
.ingredient-list { grid-template-columns: repeat(2, minmax(0, 1fr)); margin-bottom: 14px; list-style: none; }
.ingredient-list li,
.ingredient-list > span { display: flex; justify-content: space-between; gap: 8px; padding: 8px 10px; border: 1px solid rgba($color-sage-dark, .07); border-radius: $radius-sm; background: rgba($color-sage,.06); }
.step-list { padding-left: 22px; }
.step-list li { padding-left: 4px; }
.step-list li::marker { color: $color-sage; font-weight: 800; }

@media (max-width: $breakpoint-sm) {
  .card-cost {
    flex-direction: row;
    align-items: baseline;
    justify-self: start;
    min-width: 0;
    gap: 6px;
    padding: 0;
    border: 0;
    background: transparent;
  }

  .cost-value { font-size: 14px; }
  .cost-label { font-size: 12px; }
  .card-detail { padding: 14px; }
  .detail-section { padding: 14px; }
  .nutrition-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .ingredient-list { grid-template-columns: 1fr; }
}

@media (max-width: 400px) {
  .card-main {
    grid-template-columns: 68px minmax(0, 1fr) 30px;
    gap: 8px 10px;
    padding: 10px;
  }

  .recipe-visual { width: 68px; height: 88px; }
  .rank-badge { top: 5px; left: 5px; width: 30px; height: 30px; }
  .recipe-name { font-size: 15px; }
  .recipe-tags :deep(.el-tag) { padding-inline: 7px; }
  .card-expand { width: 30px; height: 30px; }
}
</style>
