<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft } from '@element-plus/icons-vue'
import { getPlanResult } from '@/api/plans'
import { getRecipeDetail } from '@/api/recipes'
import PageSkeleton from '@/components/common/PageSkeleton.vue'
import type { GeneratedRecipe, PlanResult, RecipeDetail, TopRecipe } from '@/types'

const route = useRoute()
const router = useRouter()
const result = ref<PlanResult | null>(null)
const catalogRecipe = ref<RecipeDetail | null>(null)
const loading = ref(true)
const error = ref('')
const planContextError = ref('')
const copyLabel = ref('复制做法')

const planId = computed(() => Number(route.query.plan))
const routeRecipeId = computed(() => String(route.params.id || ''))
const numericRecipeId = computed(() => /^\d+$/.test(routeRecipeId.value) ? Number(routeRecipeId.value) : null)
const planRecipe = computed<GeneratedRecipe | TopRecipe | null>(() => result.value?.recipes.find(item => (
  'recipe_key' in item
    ? item.recipe_key === routeRecipeId.value
    : String(item.recipe_id) === routeRecipeId.value
)) || null)
const generatedRecipe = computed(() => planRecipe.value && 'recipe_key' in planRecipe.value ? planRecipe.value : null)
const legacyRecipe = computed(() => planRecipe.value && !('recipe_key' in planRecipe.value) ? planRecipe.value : null)
const recipeName = computed(() => generatedRecipe.value?.name || catalogRecipe.value?.name || legacyRecipe.value?.name || '')
const description = computed(() => catalogRecipe.value?.description || generatedRecipe.value?.generation_note || legacyRecipe.value?.explanation || '')
const category = computed(() => generatedRecipe.value?.category || catalogRecipe.value?.category || legacyRecipe.value?.category || '未分类')
const cuisine = computed(() => generatedRecipe.value?.cuisine_type || catalogRecipe.value?.cuisine_type || legacyRecipe.value?.cuisine_type || '未记录')
const difficulty = computed(() => generatedRecipe.value?.difficulty || catalogRecipe.value?.difficulty || legacyRecipe.value?.difficulty || '未记录')
const categoryLabels: Record<string, string> = {
  breakfast: '早餐', main_dish: '主菜', staple: '主食', soup: '汤羹', side_dish: '配菜', light_meal: '轻食', snack: '加餐',
}
const cuisineLabels: Record<string, string> = { chinese: '中式', western: '西式' }
const difficultyLabels: Record<string, string> = { easy: '简单', medium: '适中', hard: '进阶' }
const categoryLabel = computed(() => categoryLabels[category.value] || category.value)
const cuisineLabel = computed(() => cuisineLabels[cuisine.value] || cuisine.value)
const difficultyLabel = computed(() => difficultyLabels[difficulty.value] || difficulty.value)
const prepTime = computed(() => generatedRecipe.value
  ? generatedRecipe.value.prep_time_min + generatedRecipe.value.cook_time_min
  : catalogRecipe.value
    ? catalogRecipe.value.prep_time + catalogRecipe.value.cook_time
    : legacyRecipe.value ? legacyRecipe.value.prep_time + legacyRecipe.value.cook_time : 0)
const estimatedCost = computed(() => generatedRecipe.value?.estimated_cost ?? catalogRecipe.value?.estimated_cost ?? legacyRecipe.value?.estimated_cost ?? 0)
const nutrition = computed(() => generatedRecipe.value?.nutrition || catalogRecipe.value?.nutrition || legacyRecipe.value?.nutrition || null)
const tags = computed(() => catalogRecipe.value?.tags || [])
const ingredients = computed(() => {
  if (generatedRecipe.value) {
    return generatedRecipe.value.ingredients.map(item => ({
      name: item.name,
      quantity: item.quantity,
      unit: item.unit,
      optional: item.optional,
    }))
  }
  return (catalogRecipe.value?.ingredients || []).map(item => ({
    name: item.name,
    quantity: item.quantity,
    unit: item.unit,
    optional: item.is_optional,
  }))
})
const steps = computed(() => generatedRecipe.value?.steps || [...(catalogRecipe.value?.steps || [])]
  .sort((a, b) => a.step - b.step)
  .map(item => item.content))
const sourceLabel = computed(() => generatedRecipe.value
  ? '计划即时生成'
  : catalogRecipe.value ? '标准菜谱库' : '历史计划快照')
const occurrences = computed(() => (result.value?.weekly_plan || []).flatMap(day =>
  Object.entries(day.meals).flatMap(([slot, meal]) => {
    if (!meal) return []
    const matchesId = meal.recipe_key === routeRecipeId.value || String(meal.recipe_id || '') === routeRecipeId.value
    const matchesName = !meal.recipe_key && !meal.recipe_id && meal.name === recipeName.value
    if (!matchesId && !matchesName) return []
    const mealNames: Record<string, string> = { breakfast: '早餐', lunch: '午餐', dinner: '晚餐' }
    return [`第 ${day.day} 天 · ${mealNames[slot] || slot}`]
  }),
))

async function loadRecipe() {
  loading.value = true
  error.value = ''
  planContextError.value = ''
  result.value = null
  catalogRecipe.value = null

  const tasks: Promise<void>[] = []
  let catalogError = ''

  if (numericRecipeId.value) {
    tasks.push(getRecipeDetail(numericRecipeId.value)
      .then(recipe => { catalogRecipe.value = recipe })
      .catch((cause: unknown) => { catalogError = cause instanceof Error ? cause.message : '菜谱详情加载失败' }))
  }

  if (Number.isInteger(planId.value) && planId.value > 0) {
    tasks.push(getPlanResult(planId.value)
      .then(response => { result.value = response.result })
      .catch((cause: unknown) => { planContextError.value = cause instanceof Error ? cause.message : '计划上下文加载失败' }))
  }

  await Promise.all(tasks)
  if (!recipeName.value) {
    if (!numericRecipeId.value && (!Number.isInteger(planId.value) || planId.value <= 0)) {
      error.value = '这是一份计划内生成菜谱，请从原计划进入查看。'
    } else {
      error.value = planContextError.value || catalogError || '没有找到对应菜谱'
    }
  }
  loading.value = false
}

watch(() => [route.params.id, route.query.plan], loadRecipe, { immediate: true })

async function copyRecipe() {
  if (!recipeName.value) return
  const ingredientLines = ingredients.value.map(item => `- ${item.name} ${item.quantity}${item.unit}${item.optional ? '（可选）' : ''}`)
  const stepLines = steps.value.map((step, index) => `${index + 1}. ${step}`)
  try {
    await navigator.clipboard.writeText([recipeName.value, '', '食材', ...ingredientLines, '', '做法', ...stepLines].join('\n'))
    copyLabel.value = '已复制'
    window.setTimeout(() => { copyLabel.value = '复制做法' }, 1600)
  } catch {
    copyLabel.value = '复制失败'
  }
}

function backToSource() {
  if (Number.isInteger(planId.value) && planId.value > 0) {
    router.push({ path: `/plan/${planId.value}`, query: { tab: 'today' } })
    return
  }
  router.push({ name: 'recipe-library' })
}

function nutritionValue(newKey: 'protein_g' | 'fat_g' | 'carbs_g', legacyKey: 'protein' | 'fat' | 'carbs') {
  if (!nutrition.value) return 0
  const values = nutrition.value as unknown as Record<string, unknown>
  return Number(values[newKey] ?? values[legacyKey]) || 0
}
</script>

<template>
  <div class="recipe-page page-container">
    <button class="back-link" type="button" @click="backToSource">
      <el-icon aria-hidden="true"><ArrowLeft /></el-icon>{{ planId > 0 ? '返回计划' : '返回菜谱库' }}
    </button>

    <PageSkeleton v-if="loading" :rows="4" class="recipe-skeleton" />
    <div v-else-if="error || !recipeName" class="state-card card" role="alert">
      <h1>暂时看不到这份菜谱</h1>
      <p>{{ error }}</p>
      <div><el-button type="primary" @click="loadRecipe">重新加载</el-button><el-button @click="backToSource">返回</el-button></div>
    </div>

    <article v-else class="recipe-sheet card">
      <header class="recipe-hero">
        <div>
          <span class="eyebrow">{{ sourceLabel }}</span>
          <h1>{{ recipeName }}</h1>
          <p>{{ categoryLabel }} · {{ cuisineLabel }} · {{ difficultyLabel }} · 约 {{ prepTime }} 分钟</p>
          <p v-if="description" class="recipe-description">{{ description }}</p>
          <div v-if="tags.length" class="recipe-tags" aria-label="菜谱标签"><span v-for="tag in tags" :key="tag">{{ tag }}</span></div>
        </div>
        <div class="hero-actions">
          <strong>{{ estimatedCost ? `约 ¥${estimatedCost.toFixed(1)}` : '成本待核算' }}</strong>
          <el-button plain @click="copyRecipe">{{ copyLabel }}</el-button>
        </div>
      </header>

      <section v-if="occurrences.length" class="occurrence-strip" aria-label="菜谱在计划中的安排">
        <strong>计划中安排在</strong><span v-for="item in occurrences" :key="item">{{ item }}</span>
      </section>
      <p v-else-if="planContextError && catalogRecipe" class="context-warning" role="status">菜谱做法已加载，但暂时无法读取它在计划中的出现位置。</p>

      <section v-if="nutrition" class="nutrition-strip" aria-label="每份营养信息">
        <div><strong>{{ nutrition.calories.toFixed(0) }}</strong><span>kcal</span></div>
        <div><strong>{{ nutritionValue('protein_g', 'protein').toFixed(0) }}g</strong><span>蛋白质</span></div>
        <div><strong>{{ nutritionValue('fat_g', 'fat').toFixed(0) }}g</strong><span>脂肪</span></div>
        <div><strong>{{ nutritionValue('carbs_g', 'carbs').toFixed(0) }}g</strong><span>碳水</span></div>
      </section>

      <div class="detail-grid">
        <section>
          <span class="section-index">01</span>
          <h2>准备食材</h2>
          <ul v-if="ingredients.length" class="ingredient-list">
            <li v-for="ingredient in ingredients" :key="`${ingredient.name}-${ingredient.unit}`">
              <span>{{ ingredient.name }}<small v-if="ingredient.optional">可选</small></span>
              <strong>{{ ingredient.quantity }} {{ ingredient.unit }}</strong>
            </li>
          </ul>
          <p v-else class="empty-detail">当前菜谱没有食材明细。</p>
        </section>
        <section>
          <span class="section-index">02</span>
          <h2>开始烹饪</h2>
          <ol v-if="steps.length" class="step-list">
            <li v-for="(step, index) in steps" :key="index"><span>{{ index + 1 }}</span><p>{{ step }}</p></li>
          </ol>
          <p v-else class="empty-detail">当前菜谱没有步骤明细。</p>
        </section>
      </div>
    </article>
  </div>
</template>

<style scoped lang="scss">
.recipe-page { max-width: 1060px; padding-block: 28px 96px; }
.back-link { display: inline-flex; min-height: 44px; align-items: center; gap: 7px; margin-bottom: 16px; padding: 8px 0; border: 0; background: transparent; color: $color-sage-dark; cursor: pointer; font: inherit; font-size: 14px; font-weight: 750; }
.recipe-skeleton { min-height: 430px; padding: 30px; border: 1px solid $color-border; border-radius: $radius-lg; background: $color-card; }
.state-card { display: grid; min-height: 360px; place-items: center; align-content: center; gap: 14px; padding: 38px; text-align: center; }
.state-card p { max-width: 48ch; color: $color-text-secondary; }
.recipe-sheet { overflow: hidden; }
.recipe-hero { display: flex; align-items: end; justify-content: space-between; gap: 30px; padding: clamp(28px, 5vw, 56px); background: linear-gradient(135deg, $color-surface-muted, $color-surface-warm); }
.recipe-hero > div:first-child { min-width: 0; }
.recipe-hero h1 { max-width: 700px; margin-top: 10px; font-size: clamp(38px, 6vw, 68px); letter-spacing: -.055em; line-height: 1.02; overflow-wrap: anywhere; }
.recipe-hero p { margin-top: 14px; color: $color-text-secondary; font-size: 15px; }
.recipe-hero .recipe-description { max-width: 65ch; font-size: 15px; line-height: 1.7; }
.recipe-tags { display: flex; flex-wrap: wrap; gap: 7px; margin-top: 15px; }
.recipe-tags span { padding: 5px 9px; border-radius: $radius-round; background: rgba($color-card, .72); color: $color-sage-dark; font-size: 12px; font-weight: 720; }
.hero-actions { display: grid; flex: 0 0 auto; justify-items: end; gap: 12px; }
.hero-actions strong { color: $color-rose-dark; font-size: 22px; }
.occurrence-strip { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; padding: 15px clamp(22px, 5vw, 56px); border-top: 1px solid rgba($color-sage, .12); background: $color-lime-soft; }
.occurrence-strip strong { margin-right: 4px; color: $color-sage-dark; font-size: 13px; }
.occurrence-strip span { padding: 5px 9px; border-radius: $radius-round; background: $color-card; color: $color-text-secondary; font-size: 13px; font-weight: 680; }
.context-warning { padding: 13px clamp(22px, 5vw, 56px); background: $color-surface-warm; color: $color-text-secondary; font-size: 13px; }
.nutrition-strip { display: grid; grid-template-columns: repeat(4, 1fr); border-block: 1px solid $color-divider; background: $color-card; }
.nutrition-strip div { display: grid; gap: 3px; padding: 22px; text-align: center; }
.nutrition-strip div + div { border-left: 1px solid $color-divider; }
.nutrition-strip strong { font-size: 22px; font-variant-numeric: tabular-nums; }
.nutrition-strip span { color: $color-text-secondary; font-size: 12px; }
.detail-grid { display: grid; grid-template-columns: minmax(280px, .75fr) minmax(0, 1.25fr); gap: 48px; padding: clamp(28px, 5vw, 56px); }
.section-index { color: $color-rose-dark; font-size: 12px; font-weight: 850; letter-spacing: .1em; }
.detail-grid h2 { margin: 6px 0 20px; font-size: 26px; }
.ingredient-list { display: grid; gap: 8px; list-style: none; }
.ingredient-list li { display: flex; justify-content: space-between; gap: 12px; padding: 12px 14px; border-radius: $radius-sm; background: $color-surface-soft; font-size: 15px; }
.ingredient-list li > span { min-width: 0; overflow-wrap: anywhere; }
.ingredient-list small { margin-left: 7px; color: $color-text-placeholder; font-size: 12px; }
.ingredient-list strong { flex: 0 0 auto; white-space: nowrap; }
.step-list { display: grid; gap: 18px; list-style: none; }
.step-list li { display: grid; grid-template-columns: 36px minmax(0, 1fr); align-items: start; gap: 12px; }
.step-list li > span { display: grid; width: 36px; height: 36px; place-items: center; border-radius: 12px; background: $color-sage-dark; color: $color-text-inverse; font-size: 12px; font-weight: 800; }
.step-list p { padding-top: 5px; color: $color-text-primary; font-size: 16px; line-height: 1.72; }
.empty-detail { padding: 18px; border: 1px dashed $color-border; border-radius: $radius-sm; color: $color-text-secondary; font-size: 14px; }

@media (max-width: $breakpoint-sm) {
  .recipe-page { padding-block: 18px 64px; }
  .recipe-hero { align-items: flex-start; flex-direction: column; }
  .recipe-hero h1 { font-size: 39px; }
  .recipe-hero p, .recipe-hero .recipe-description { font-size: 16px; }
  .hero-actions { width: 100%; grid-template-columns: 1fr auto; align-items: center; justify-items: start; }
  .nutrition-strip { grid-template-columns: repeat(2, 1fr); }
  .nutrition-strip div:nth-child(3) { border-left: 0; border-top: 1px solid $color-divider; }
  .nutrition-strip div:nth-child(4) { border-top: 1px solid $color-divider; }
  .detail-grid { grid-template-columns: 1fr; gap: 38px; }
}
</style>
