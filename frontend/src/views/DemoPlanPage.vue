<script setup lang="ts">
import { useRouter } from 'vue-router'
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
]

const nutritionReport: NutritionReportType = {
  avg_daily_calories: 1650,
  total_calories: 11550,
  protein_g: 118,
  fat_g: 52,
  carbs_g: 190,
  fiber_g: 28,
  protein_pct: .34,
  fat_pct: .28,
  carbs_pct: .38,
  recommendation: '整体蛋白质充足，建议每天补充足量饮水，并根据运动量微调主食份量。',
}

const shoppingList: ShoppingListType = {
  total_cost: 186,
  items: [],
  by_category: {
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
  },
}
</script>

<template>
  <main class="demo-page page-container">
    <section class="demo-hero">
      <div>
        <div class="demo-kicker"><PremiumIcon name="plan" :size="15" :box-size="30" />只读方案示例</div>
        <h1>减脂期 · 7 天轻盈饮食计划</h1>
        <p>这是 NutriGenie 根据“减脂、预算 300 元、高蛋白”生成的示例方案，用来快速了解最终结果页。</p>
      </div>
      <span class="demo-badge">示例数据</span>
    </section>

    <section class="overview-card card">
      <div><strong>1650</strong><span>日均 kcal</span></div>
      <div><strong>118g</strong><span>日均蛋白质</span></div>
      <div><strong>¥186</strong><span>预计采购</span></div>
      <div><strong>7 天</strong><span>规划周期</span></div>
    </section>

    <section class="demo-section">
      <h2 class="section-title"><PremiumIcon name="trophy" :size="17" :box-size="34" />精选菜谱 <small>按综合匹配度排序</small></h2>
      <div class="recipe-list">
        <RecipeCard v-for="(recipe, index) in topRecipes" :key="recipe.recipe_id" :recipe="recipe" :rank="index + 1" />
      </div>
    </section>

    <section class="demo-section">
      <WeeklyTimeline :weekly-plan="weeklyPlan" />
    </section>

    <section class="detail-grid demo-section">
      <div class="panel-card card"><NutritionReport :report="nutritionReport" /></div>
      <div class="panel-card card"><ShoppingList :shopping-list="shoppingList" /></div>
    </section>

    <section class="summary-card card">
      <div class="summary-heading"><PremiumIcon name="clipboard" :size="17" :box-size="32" /><h2>AI 方案总结</h2></div>
      <p>这套方案以高蛋白、适中碳水和可执行预算为核心，优先安排鸡胸肉、虾仁、鸡蛋等易获得食材，并用不同烹饪方式保持三餐的新鲜感。</p>
      <el-button type="primary" round size="large" @click="router.push('/profile')">创建我的专属方案</el-button>
    </section>
  </main>
</template>

<style scoped lang="scss">
.demo-page { max-width: 980px; padding: 36px 20px 80px; }

.demo-hero {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 24px;
  margin-bottom: 20px;
  padding: 32px;
  border-radius: $radius-xl;
  background: linear-gradient(135deg, rgba($color-sage, .18), rgba($color-rose-light, .24));
  border: 1px solid rgba(255,255,255,.7);
  box-shadow: $shadow-md;
}

.demo-kicker { display: flex; align-items: center; gap: 9px; color: $color-sage-dark; font-size: 13px; font-weight: 700; }
.demo-kicker .premium-icon { border-radius: 10px; box-shadow: none; }
.demo-hero h1 { margin-top: 14px; color: $color-text-primary; font-size: clamp(26px, 4vw, 38px); line-height: 1.2; }
.demo-hero p { max-width: 620px; margin-top: 12px; color: $color-text-secondary; font-size: 14px; line-height: 1.8; }
.demo-badge { padding: 7px 12px; border-radius: 999px; color: $color-sage-dark; background: rgba(255,255,255,.68); font-size: 12px; font-weight: 700; white-space: nowrap; }

.overview-card { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 40px; padding: 18px; }
.overview-card div { display: flex; flex-direction: column; gap: 3px; padding: 12px 14px; border-radius: $radius-md; background: rgba($color-sage, .06); }
.overview-card strong { color: $color-text-primary; font-size: 22px; }
.overview-card span { color: $color-text-secondary; font-size: 12px; }

.demo-section { margin-bottom: 38px; }
.section-title { display: flex; align-items: center; gap: 9px; margin-bottom: 16px; color: $color-text-primary; font-size: 20px; }
.section-title .premium-icon { border-radius: 10px; box-shadow: none; }
.section-title small { color: $color-text-secondary; font-size: 12px; font-weight: 400; }
.recipe-list { display: flex; flex-direction: column; gap: 10px; }

.detail-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 20px; }
.panel-card { padding: 22px; }
.summary-card { margin-top: 4px; padding: 26px; }
.summary-heading { display: flex; align-items: center; gap: 9px; margin-bottom: 12px; }
.summary-heading .premium-icon { border-radius: 10px; box-shadow: none; }
.summary-heading h2 { color: $color-text-primary; font-size: 20px; }
.summary-card p { margin-bottom: 20px; color: $color-text-secondary; font-size: 14px; line-height: 1.8; }

@media (max-width: $breakpoint-sm) {
  .demo-page { padding-top: 24px; }
  .demo-hero { flex-direction: column; padding: 24px; }
  .overview-card { grid-template-columns: repeat(2, 1fr); }
  .detail-grid { grid-template-columns: 1fr; }
}
</style>
