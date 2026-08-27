<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import PremiumIcon from '@/components/common/PremiumIcon.vue'
import RecipeCard from '@/components/recipe/RecipeCard.vue'
import WeeklyTimeline from '@/components/plan/WeeklyTimeline.vue'
import NutritionReport from '@/components/plan/NutritionReport.vue'
import ShoppingList from '@/components/plan/ShoppingList.vue'
import type {
  MealItem,
  MealNutrition,
  NutritionReport as NutritionReportType,
  ShoppingList as ShoppingListType,
  TopRecipe,
  WeeklyDay,
} from '@/types'

const router = useRouter()
const auth = useAuthStore()

const topRecipes: TopRecipe[] = [
  {
    recipe_id: 1,
    name: '香煎鸡胸藜麦碗',
    image_url: null,
    category: 'main_dish',
    cuisine_type: '家常菜',
    difficulty: 'easy',
    prep_time: 10,
    cook_time: 15,
    scores: { health: .96, budget: .88, preference: .93, season: .86, variety: .82, utilization: .91, semantic: .95 },
    total_score: .92,
    nutrition: { calories: 520, protein: 42, fat: 16, carbs: 48, fiber: 8 },
    estimated_cost: 18,
    explanation: '蛋白质充足、碳水适中，搭配藜麦和时蔬，适合减脂期的主餐。',
    evidence: { matched_preferences: ['减脂友好', '高蛋白'], objective_evidence: [], retrieval_sources: ['营养约束', '菜谱知识库'], warnings: [] },
  },
  {
    recipe_id: 2,
    name: '番茄虾仁全麦意面',
    image_url: null,
    category: 'main_dish',
    cuisine_type: '西式',
    difficulty: 'easy',
    prep_time: 8,
    cook_time: 18,
    scores: { health: .91, budget: .84, preference: .9, season: .88, variety: .94, utilization: .85, semantic: .9 },
    total_score: .89,
    nutrition: { calories: 560, protein: 35, fat: 14, carbs: 66, fiber: 9 },
    estimated_cost: 22,
    explanation: '全麦主食配合虾仁和番茄，口感丰富，能量释放更平稳。',
    evidence: { matched_preferences: ['高纤维', '低油'], objective_evidence: [], retrieval_sources: ['营养约束', '季节食材'], warnings: [] },
  },
  {
    recipe_id: 3,
    name: '香菇豆腐荞麦面',
    image_url: null,
    category: 'light_meal',
    cuisine_type: '日式',
    difficulty: 'easy',
    prep_time: 10,
    cook_time: 12,
    scores: { health: .9, budget: .97, preference: .86, season: .9, variety: .92, utilization: .94, semantic: .87 },
    total_score: .88,
    nutrition: { calories: 430, protein: 24, fat: 12, carbs: 58, fiber: 10 },
    estimated_cost: 13,
    explanation: '植物蛋白和菌菇提供饱腹感，预算友好，适合作为轻盈晚餐。',
    evidence: { matched_preferences: ['预算友好', '高纤维'], objective_evidence: [], retrieval_sources: ['预算约束', '菜谱知识库'], warnings: [] },
  },
]

function meal(recipeId: number, name: string, nutrition: MealNutrition, servingSize = 1): MealItem {
  return { recipe_id: recipeId, name, nutrition, serving_size: servingSize }
}

const weeklyPlan: WeeklyDay[] = [
  {
    day: 1,
    meals: {
      breakfast: meal(3, '无糖酸奶坚果杯', { calories: 320, protein: 18, fat: 12, carbs: 32 }),
      lunch: meal(1, '香煎鸡胸藜麦碗', { calories: 520, protein: 42, fat: 16, carbs: 48 }),
      dinner: meal(3, '香菇豆腐荞麦面', { calories: 430, protein: 24, fat: 12, carbs: 58 }),
    },
    total_nutrition: { calories: 1270, protein_g: 84, fat_g: 40, carbs_g: 138, fiber_g: 24 },
  },
  {
    day: 2,
    meals: {
      breakfast: meal(2, '番茄鸡蛋全麦吐司', { calories: 360, protein: 22, fat: 13, carbs: 42 }),
      lunch: meal(2, '番茄虾仁全麦意面', { calories: 560, protein: 35, fat: 14, carbs: 66 }),
      dinner: meal(1, '鸡胸肉蔬菜卷', { calories: 480, protein: 38, fat: 15, carbs: 42 }),
    },
    total_nutrition: { calories: 1400, protein_g: 95, fat_g: 42, carbs_g: 150, fiber_g: 26 },
  },
  {
    day: 3,
    meals: {
      breakfast: meal(1, '鸡蛋菠菜全麦卷', { calories: 350, protein: 24, fat: 14, carbs: 34 }),
      lunch: meal(1, '香煎鸡胸藜麦碗', { calories: 520, protein: 42, fat: 16, carbs: 48 }),
      dinner: meal(2, '虾仁番茄沙拉', { calories: 410, protein: 30, fat: 12, carbs: 38 }),
    },
    total_nutrition: { calories: 1280, protein_g: 96, fat_g: 42, carbs_g: 120, fiber_g: 24 },
  },
  {
    day: 4,
    meals: {
      breakfast: meal(2, '燕麦蓝莓酸奶碗', { calories: 380, protein: 22, fat: 10, carbs: 52 }),
      lunch: meal(2, '番茄虾仁全麦意面', { calories: 560, protein: 35, fat: 14, carbs: 66 }),
      dinner: meal(3, '香菇豆腐荞麦面', { calories: 430, protein: 24, fat: 12, carbs: 58 }),
    },
    total_nutrition: { calories: 1370, protein_g: 81, fat_g: 36, carbs_g: 176, fiber_g: 27 },
  },
  {
    day: 5,
    meals: {
      breakfast: meal(1, '鸡蛋菠菜全麦卷', { calories: 350, protein: 24, fat: 14, carbs: 34 }),
      lunch: meal(1, '香煎鸡胸藜麦碗', { calories: 520, protein: 42, fat: 16, carbs: 48 }),
      dinner: meal(2, '南瓜虾仁浓汤', { calories: 440, protein: 31, fat: 13, carbs: 48 }),
    },
    total_nutrition: { calories: 1310, protein_g: 97, fat_g: 43, carbs_g: 130, fiber_g: 25 },
  },
  {
    day: 6,
    meals: {
      breakfast: meal(3, '无糖酸奶坚果杯', { calories: 320, protein: 18, fat: 12, carbs: 32 }),
      lunch: meal(3, '香菇豆腐荞麦面', { calories: 430, protein: 24, fat: 12, carbs: 58 }),
      dinner: meal(1, '鸡胸肉时蔬饭', { calories: 540, protein: 44, fat: 15, carbs: 55 }),
    },
    total_nutrition: { calories: 1290, protein_g: 86, fat_g: 39, carbs_g: 145, fiber_g: 24 },
  },
  {
    day: 7,
    meals: {
      breakfast: meal(2, '番茄鸡蛋全麦吐司', { calories: 360, protein: 22, fat: 13, carbs: 42 }),
      lunch: meal(1, '香煎鸡胸藜麦碗', { calories: 520, protein: 42, fat: 16, carbs: 48 }),
      dinner: meal(2, '虾仁番茄沙拉', { calories: 410, protein: 30, fat: 12, carbs: 38 }),
    },
    total_nutrition: { calories: 1290, protein_g: 94, fat_g: 41, carbs_g: 128, fiber_g: 23 },
  },
]

const nutritionReport = computed<NutritionReportType>(() => {
  const totals = weeklyPlan.reduce((sum, day) => ({
    calories: sum.calories + day.total_nutrition.calories,
    protein: sum.protein + day.total_nutrition.protein_g,
    fat: sum.fat + day.total_nutrition.fat_g,
    carbs: sum.carbs + day.total_nutrition.carbs_g,
  }), { calories: 0, protein: 0, fat: 0, carbs: 0 })
  const protein = totals.protein / weeklyPlan.length
  const fat = totals.fat / weeklyPlan.length
  const carbs = totals.carbs / weeklyPlan.length
  const macroEnergy = protein * 4 + fat * 9 + carbs * 4
  return {
    avg_daily_calories: totals.calories / weeklyPlan.length,
    total_calories: totals.calories,
    protein_g: protein,
    fat_g: fat,
    carbs_g: carbs,
    fiber_g: 28,
    protein_pct: protein * 4 / macroEnergy,
    fat_pct: fat * 9 / macroEnergy,
    carbs_pct: carbs * 4 / macroEnergy,
    recommendation: '整体蛋白质充足，建议每天补充足量饮水，并根据运动量微调主食份量。',
  }
})

const shoppingCategories: ShoppingListType['by_category'] = {
    '蛋白质': [
      { name: '鸡胸肉', quantity: 1000, unit: 'g', estimated_cost: 42 },
      { name: '虾仁', quantity: 500, unit: 'g', estimated_cost: 38 },
      { name: '鸡蛋', quantity: 10, unit: '枚', estimated_cost: 18 },
    ],
    '蔬菜水果': [
      { name: '番茄', quantity: 800, unit: 'g', estimated_cost: 12 },
      { name: '菠菜', quantity: 400, unit: 'g', estimated_cost: 10 },
      { name: '西兰花', quantity: 500, unit: 'g', estimated_cost: 16 },
    ],
    '主食与调味': [
      { name: '藜麦', quantity: 500, unit: 'g', estimated_cost: 28 },
      { name: '全麦意面', quantity: 500, unit: 'g', estimated_cost: 15 },
      { name: '低脂芝麻酱', quantity: 1, unit: '瓶', estimated_cost: 17 },
    ],
}
const shoppingList = computed<ShoppingListType>(() => ({
  total_cost: Object.values(shoppingCategories).flat().reduce((sum, item) => sum + item.estimated_cost, 0),
  items: [],
  by_category: shoppingCategories,
}))
const overview = computed(() => ({
  calories: nutritionReport.value.avg_daily_calories,
  protein: nutritionReport.value.protein_g,
  cost: shoppingList.value.total_cost,
}))

function createMyPlan() {
  if (auth.isLoggedIn) router.push('/profile')
  else router.push({ name: 'auth', query: { mode: 'register', redirect: '/profile' } })
}
</script>

<template>
  <div class="demo-page page-container">
    <section class="demo-hero">
      <div class="demo-hero-copy">
        <div class="demo-kicker"><PremiumIcon name="plan" :size="15" :box-size="30" />只读方案示例</div>
        <h1>减脂期 · 7 天轻盈饮食计划</h1>
        <p>这是 NutriGenie 根据“减脂、预算 300 元、高蛋白”生成的示例方案，用来快速了解最终结果页。</p>
      </div>
      <aside class="demo-hero-meta" aria-label="方案条件">
        <span class="demo-badge">示例数据</span>
        <span>减脂目标</span>
        <span>预算 ¥300</span>
        <span>高蛋白</span>
      </aside>
    </section>

    <section class="overview-card card" aria-label="方案核心指标">
      <div class="overview-item overview-item--calories"><strong>{{ overview.calories.toFixed(0) }}</strong><span>日均 kcal</span></div>
      <div class="overview-item overview-item--protein"><strong>{{ overview.protein.toFixed(0) }}g</strong><span>日均蛋白质</span></div>
      <div class="overview-item overview-item--cost"><strong>¥{{ overview.cost.toFixed(0) }}</strong><span>预计采购</span></div>
      <div class="overview-item overview-item--days"><strong>7 天</strong><span>规划周期</span></div>
    </section>

    <section class="demo-section">
      <h2 class="section-title"><PremiumIcon name="trophy" :size="17" :box-size="34" />精选菜谱 <small>按综合匹配度排序</small></h2>
      <div class="recipe-list">
        <RecipeCard v-for="(recipe, index) in topRecipes" :key="recipe.recipe_id" :recipe="recipe" :rank="index + 1" :enable-detail="false" />
      </div>
    </section>

    <section class="demo-section">
      <WeeklyTimeline :weekly-plan="weeklyPlan" />
    </section>

    <section class="detail-grid demo-section">
      <div class="panel-card card"><NutritionReport :report="nutritionReport" :target-range="[1250, 1450]" /></div>
      <div class="panel-card card"><ShoppingList :shopping-list="shoppingList" /></div>
    </section>

    <section class="summary-card card">
      <div class="summary-heading"><PremiumIcon name="clipboard" :size="17" :box-size="32" /><h2>AI 方案总结</h2></div>
      <p>这套方案以高蛋白、适中碳水和可执行预算为核心，优先安排鸡胸肉、虾仁、鸡蛋等易获得食材，并用不同烹饪方式保持三餐的新鲜感。</p>
      <el-button class="summary-action" type="primary" round size="large" @click="createMyPlan">创建我的专属方案</el-button>
    </section>
  </div>
</template>

<style scoped lang="scss">
.demo-page { max-width: 1120px; padding-top: clamp(28px, 5vw, 56px); padding-bottom: 88px; }

.demo-hero {
  position: relative;
  display: flex;
  align-items: stretch;
  justify-content: space-between;
  gap: clamp(24px, 5vw, 64px);
  margin-bottom: 18px;
  padding: clamp(28px, 5vw, 52px);
  overflow: hidden;
  border: 1px solid rgba($color-sage-dark, .12);
  border-radius: $radius-xl;
  background:
    radial-gradient(circle at 92% 8%, rgba($color-lime, .4), transparent 15rem),
    linear-gradient(135deg, rgba($color-sage-light, .8), rgba($color-surface-warm, .82));
  box-shadow: $shadow-lg;

  &::after {
    position: absolute;
    right: -56px;
    bottom: -86px;
    width: 220px;
    height: 220px;
    border: 1px solid rgba($color-card, .68);
    border-radius: 50%;
    content: '';
  }
}

.demo-hero-copy { position: relative; z-index: 1; max-width: 680px; }
.demo-kicker { display: flex; align-items: center; gap: 9px; color: $color-sage-dark; font-size: 13px; font-weight: 700; }
.demo-kicker .premium-icon { border-radius: 10px; box-shadow: none; }
.demo-hero h1 { max-width: 620px; margin-top: 16px; color: $color-text-primary; font-size: clamp(30px, 4.8vw, 50px); letter-spacing: -.035em; line-height: 1.12; }
.demo-hero p { max-width: 620px; margin-top: 16px; color: $color-text-secondary; font-size: 15px; line-height: 1.8; }
.demo-hero-meta { position: relative; z-index: 1; display: flex; flex: 0 0 152px; flex-direction: column; justify-content: center; gap: 9px; padding: 18px; border: 1px solid rgba($color-card,.72); border-radius: $radius-lg; background: rgba($color-card,.58); box-shadow: inset 0 1px 0 rgba(255,255,255,.7); backdrop-filter: blur(8px); }
.demo-hero-meta > span:not(.demo-badge) { color: $color-text-secondary; font-size: 12px; font-weight: 650; }
.demo-hero-meta > span:not(.demo-badge)::before { display: inline-block; width: 6px; height: 6px; margin-right: 7px; border-radius: 50%; background: $color-sage; content: ''; }
.demo-badge { align-self: flex-start; margin-bottom: 4px; padding: 6px 10px; border-radius: 999px; color: $color-text-inverse; background: $color-sage-dark; font-size: 11px; font-weight: 750; white-space: nowrap; }

.overview-card { position: relative; z-index: 2; display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; margin: -10px 18px 48px; padding: 12px; }
.overview-item { position: relative; display: flex; flex-direction: column; gap: 3px; overflow: hidden; padding: 15px 16px; border-radius: $radius-md; background: $color-surface-soft; }
.overview-item::before { position: absolute; top: 0; right: 0; left: 0; height: 3px; background: $color-sage; content: ''; }
.overview-item--protein { background: rgba($score-utilization,.07); &::before { background: $score-utilization; } }
.overview-item--cost { background: $color-surface-warm; &::before { background: $color-rose; } }
.overview-item--days { background: $color-blue-soft; &::before { background: $color-blue; } }
.overview-card strong { color: $color-text-primary; font-size: 23px; font-variant-numeric: tabular-nums; font-weight: 800; }
.overview-card span { color: $color-text-secondary; font-size: 12px; }

.demo-section { margin-bottom: 48px; }
.section-title { display: flex; align-items: center; gap: 9px; margin-bottom: 18px; color: $color-text-primary; font-size: 21px; font-weight: 750; }
.section-title .premium-icon { border-radius: 10px; box-shadow: none; }
.section-title small { color: $color-text-secondary; font-size: 12px; font-weight: 400; }
.recipe-list { display: flex; flex-direction: column; gap: 12px; }

.detail-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); align-items: start; gap: 20px; }
.panel-card { padding: clamp(18px, 3vw, 24px); }
.summary-card { position: relative; overflow: hidden; margin-top: 4px; padding: clamp(24px, 4vw, 34px); border-color: rgba($color-sage,.2); background: linear-gradient(135deg, rgba($color-card,.96), rgba($color-lime-soft,.42)); }
.summary-card::after { position: absolute; right: -64px; bottom: -84px; width: 190px; height: 190px; border: 24px solid rgba($color-lime,.16); border-radius: 50%; content: ''; pointer-events: none; }
.summary-heading { display: flex; align-items: center; gap: 9px; margin-bottom: 12px; }
.summary-heading .premium-icon { border-radius: 10px; box-shadow: none; }
.summary-heading h2 { color: $color-text-primary; font-size: 20px; }
.summary-card p { position: relative; z-index: 1; max-width: 760px; margin-bottom: 22px; color: $color-text-secondary; font-size: 14px; line-height: 1.8; }
.summary-action { position: relative; z-index: 1; }

@media (max-width: $breakpoint-sm) {
  .demo-page { padding-top: 24px; }
  .demo-hero { flex-direction: column; padding: 26px 22px; }
  .demo-hero-meta { display: grid; grid-template-columns: repeat(3, auto); flex: none; gap: 8px 12px; padding: 13px; }
  .demo-badge { grid-column: 1 / -1; }
  .overview-card { grid-template-columns: repeat(2, minmax(0, 1fr)); margin: 12px 0 40px; }
  .detail-grid { grid-template-columns: 1fr; }
  .section-title { align-items: flex-start; flex-wrap: wrap; }
  .section-title small { width: 100%; padding-left: 43px; }
  .summary-action { width: 100%; }
}

@media (max-width: 400px) {
  .demo-hero-meta { grid-template-columns: 1fr; }
  .demo-badge { grid-column: auto; }
  .overview-card { gap: 8px; padding: 9px; }
  .overview-item { padding: 13px 12px; }
  .overview-card strong { font-size: 20px; }
}
</style>
