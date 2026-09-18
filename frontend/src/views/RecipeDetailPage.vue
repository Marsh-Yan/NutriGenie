<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getPlanResult } from '@/api/plans'
import type { GeneratedRecipe, PlanResult, TopRecipe } from '@/types'

const route = useRoute()
const router = useRouter()
const result = ref<PlanResult | null>(null)
const loading = ref(true)
const error = ref('')
const copyLabel = ref('复制做法')

const planId = computed(() => Number(route.query.plan))
const recipe = computed<GeneratedRecipe | TopRecipe | null>(() => {
  const id = String(route.params.id)
  return result.value?.recipes.find(item => (
    'recipe_key' in item ? item.recipe_key === id : String(item.recipe_id) === id
  )) || null
})
const generatedRecipe = computed(() => recipe.value && 'recipe_key' in recipe.value ? recipe.value : null)
const legacyRecipe = computed(() => recipe.value && !('recipe_key' in recipe.value) ? recipe.value : null)
const nutrition = computed(() => generatedRecipe.value?.nutrition || recipe.value?.nutrition || null)
const prepTime = computed(() => generatedRecipe.value
  ? generatedRecipe.value.prep_time_min + generatedRecipe.value.cook_time_min
  : legacyRecipe.value ? legacyRecipe.value.prep_time + legacyRecipe.value.cook_time : 0)

onMounted(async () => {
  if (!Number.isInteger(planId.value) || planId.value <= 0) {
    error.value = '缺少有效的计划编号'
    loading.value = false
    return
  }
  try {
    const response = await getPlanResult(planId.value)
    result.value = response.result
    if (!response.result) error.value = '计划仍在生成，暂时无法读取菜谱'
    else if (!recipe.value) error.value = '这份计划中没有找到对应菜谱'
  } catch (cause: unknown) {
    error.value = cause instanceof Error ? cause.message : '菜谱加载失败'
  } finally {
    loading.value = false
  }
})

async function copyRecipe() {
  if (!recipe.value) return
  const ingredients = generatedRecipe.value?.ingredients.map(item => `- ${item.name} ${item.quantity}${item.unit}`) || []
  const steps = generatedRecipe.value?.steps.map((step, index) => `${index + 1}. ${step}`) || []
  try {
    await navigator.clipboard.writeText([recipe.value.name, '', '食材', ...ingredients, '', '做法', ...steps].join('\n'))
    copyLabel.value = '已复制'
    window.setTimeout(() => { copyLabel.value = '复制做法' }, 1600)
  } catch {
    copyLabel.value = '复制失败'
  }
}

function backToPlan() {
  if (planId.value) router.push({ path: `/plan/${planId.value}`, query: { tab: 'today' } })
  else router.push('/plans')
}
</script>

<template>
  <div class="recipe-page page-container">
    <button class="back-link" type="button" @click="backToPlan">← 返回计划</button>

    <div v-if="loading" class="state-card card" aria-live="polite">正在加载菜谱…</div>
    <div v-else-if="error || !recipe" class="state-card card" role="alert">
      <h1>暂时看不到这份菜谱</h1>
      <p>{{ error }}</p>
      <el-button type="primary" @click="backToPlan">回到计划</el-button>
    </div>

    <article v-else class="recipe-sheet card">
      <header class="recipe-hero">
        <div>
          <span class="eyebrow">计划内菜谱</span>
          <h1>{{ recipe.name }}</h1>
          <p>{{ recipe.category }} · {{ recipe.cuisine_type }} · 约 {{ prepTime }} 分钟</p>
        </div>
        <div class="hero-actions">
          <strong>约 ¥{{ recipe.estimated_cost.toFixed(1) }}</strong>
          <el-button plain @click="copyRecipe">{{ copyLabel }}</el-button>
        </div>
      </header>

      <section v-if="nutrition" class="nutrition-strip" aria-label="营养信息">
        <div><strong>{{ nutrition.calories.toFixed(0) }}</strong><span>kcal</span></div>
        <div><strong>{{ ('protein_g' in nutrition ? nutrition.protein_g : nutrition.protein).toFixed(0) }}g</strong><span>蛋白质</span></div>
        <div><strong>{{ ('fat_g' in nutrition ? nutrition.fat_g : nutrition.fat).toFixed(0) }}g</strong><span>脂肪</span></div>
        <div><strong>{{ ('carbs_g' in nutrition ? nutrition.carbs_g : nutrition.carbs).toFixed(0) }}g</strong><span>碳水</span></div>
      </section>

      <div v-if="generatedRecipe" class="detail-grid">
        <section>
          <span class="section-index">01</span>
          <h2>准备食材</h2>
          <ul class="ingredient-list">
            <li v-for="ingredient in generatedRecipe.ingredients" :key="`${ingredient.name}-${ingredient.unit}`">
              <span>{{ ingredient.name }}</span><strong>{{ ingredient.quantity }} {{ ingredient.unit }}</strong>
            </li>
          </ul>
        </section>
        <section>
          <span class="section-index">02</span>
          <h2>开始烹饪</h2>
          <ol class="step-list">
            <li v-for="(step, index) in generatedRecipe.steps" :key="index"><span>{{ index + 1 }}</span><p>{{ step }}</p></li>
          </ol>
        </section>
      </div>
      <p v-else class="legacy-note">这是历史版本菜谱，当前仅保留营养与成本摘要。</p>
    </article>
  </div>
</template>

<style scoped lang="scss">
.recipe-page { max-width: 1060px; padding-block: 28px 96px; }
.back-link { min-height: 44px; margin-bottom: 16px; padding: 8px 0; border: 0; background: transparent; color: $color-sage-dark; cursor: pointer; font: inherit; font-size: 14px; font-weight: 750; }
.state-card { display: grid; min-height: 360px; place-items: center; align-content: center; gap: 14px; padding: 38px; text-align: center; }
.state-card p { color: $color-text-secondary; }
.recipe-sheet { overflow: hidden; }
.recipe-hero { display: flex; align-items: end; justify-content: space-between; gap: 30px; padding: clamp(28px, 5vw, 56px); background: linear-gradient(135deg, $color-surface-muted, $color-surface-warm); }
.recipe-hero h1 { max-width: 700px; margin-top: 10px; font-size: clamp(38px, 6vw, 68px); letter-spacing: -.055em; line-height: 1.02; }
.recipe-hero p { margin-top: 14px; color: $color-text-secondary; font-size: 15px; }
.hero-actions { display: grid; justify-items: end; gap: 12px; }
.hero-actions strong { color: $color-rose-dark; font-size: 22px; }
.nutrition-strip { display: grid; grid-template-columns: repeat(4, 1fr); border-block: 1px solid $color-divider; background: $color-card; }
.nutrition-strip div { display: grid; gap: 3px; padding: 22px; text-align: center; }
.nutrition-strip div + div { border-left: 1px solid $color-divider; }
.nutrition-strip strong { font-size: 22px; font-variant-numeric: tabular-nums; }
.nutrition-strip span { color: $color-text-secondary; font-size: 12px; }
.detail-grid { display: grid; grid-template-columns: minmax(280px, .75fr) minmax(0, 1.25fr); gap: 48px; padding: clamp(28px, 5vw, 56px); }
.section-index { color: $color-rose-dark; font-size: 12px; font-weight: 850; letter-spacing: .1em; }
.detail-grid h2 { margin: 6px 0 20px; font-size: 26px; }
.ingredient-list { display: grid; gap: 8px; list-style: none; }
.ingredient-list li { display: flex; justify-content: space-between; gap: 12px; padding: 12px 14px; border-radius: $radius-sm; background: $color-surface-soft; font-size: 14px; }
.ingredient-list strong { white-space: nowrap; }
.step-list { display: grid; gap: 18px; list-style: none; }
.step-list li { display: grid; grid-template-columns: 36px minmax(0, 1fr); align-items: start; gap: 12px; }
.step-list li > span { display: grid; width: 36px; height: 36px; place-items: center; border-radius: 12px; background: $color-sage-dark; color: $color-text-inverse; font-size: 12px; font-weight: 800; }
.step-list p { padding-top: 6px; color: $color-text-primary; font-size: 15px; line-height: 1.75; }
.legacy-note { margin: 32px; padding: 20px; border-radius: $radius-md; background: $color-surface-soft; color: $color-text-secondary; text-align: center; }

@media (max-width: $breakpoint-sm) {
  .recipe-page { padding-block: 18px 64px; }
  .recipe-hero { align-items: flex-start; flex-direction: column; }
  .recipe-hero h1 { font-size: 39px; }
  .hero-actions { width: 100%; grid-template-columns: 1fr auto; align-items: center; justify-items: start; }
  .nutrition-strip { grid-template-columns: repeat(2, 1fr); }
  .nutrition-strip div:nth-child(3) { border-left: 0; border-top: 1px solid $color-divider; }
  .nutrition-strip div:nth-child(4) { border-top: 1px solid $color-divider; }
  .detail-grid { grid-template-columns: 1fr; gap: 38px; }
}
</style>
