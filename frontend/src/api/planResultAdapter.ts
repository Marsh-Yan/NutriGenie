import type {
  GeneratedNutrition,
  GenerationMeta,
  NutritionReport,
  PlanResult,
  PlanValidation,
  ShoppingList,
  TopRecipe,
  WeeklyDay,
} from '@/types'

type JsonObject = Record<string, any>

function object(value: unknown): JsonObject {
  return value && typeof value === 'object' && !Array.isArray(value)
    ? value as JsonObject
    : {}
}

function number(value: unknown): number {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : 0
}

function stringList(value: unknown): string[] {
  return Array.isArray(value) ? value.map(item => String(item)) : []
}

function nutrition(value: unknown): GeneratedNutrition {
  const item = object(value)
  return {
    calories: number(item.calories),
    protein_g: number(item.protein_g ?? item.protein),
    fat_g: number(item.fat_g ?? item.fat),
    carbs_g: number(item.carbs_g ?? item.carbs),
    fiber_g: number(item.fiber_g ?? item.fiber),
  }
}

function weeklyPlan(value: unknown): WeeklyDay[] {
  if (!Array.isArray(value)) return []
  return value.map((rawDay) => {
    const day = object(rawDay)
    const meals = object(day.meals)
    return {
      day: number(day.day),
      meals: Object.fromEntries(Object.entries(meals).map(([slot, rawMeal]) => {
        if (!rawMeal) return [slot, null]
        const meal = object(rawMeal)
        return [slot, {
          recipe_key: typeof meal.recipe_key === 'string' ? meal.recipe_key : undefined,
          recipe_id: meal.recipe_id == null ? undefined : number(meal.recipe_id),
          name: String(meal.name || '未命名菜品'),
          serving_size: Math.max(1, number(meal.serving_size) || 1),
          nutrition: nutrition(meal.nutrition),
        }]
      })),
      total_nutrition: nutrition(day.total_nutrition),
    }
  })
}

function nutritionReport(value: unknown): NutritionReport {
  const report = object(value)
  return {
    avg_daily_calories: number(report.avg_daily_calories),
    total_calories: number(report.total_calories),
    protein_g: number(report.protein_g ?? report.protein),
    fat_g: number(report.fat_g ?? report.fat),
    carbs_g: number(report.carbs_g ?? report.carbs),
    fiber_g: number(report.fiber_g ?? report.fiber),
    protein_pct: number(report.protein_pct),
    fat_pct: number(report.fat_pct),
    carbs_pct: number(report.carbs_pct),
    recommendation: String(report.recommendation || ''),
  }
}

function shoppingList(value: unknown): ShoppingList {
  const shopping = object(value)
  return {
    total_cost: number(shopping.total_cost),
    items: Array.isArray(shopping.items) ? shopping.items : [],
    by_category: object(shopping.by_category),
  }
}

function legacyValidation(value: unknown): PlanValidation {
  const raw = object(value)
  const warnings = stringList(raw.warnings)
  const passed = Boolean(raw.passed)
  return {
    status: passed ? (warnings.length ? 'warning' : 'passed') : 'failed',
    passed,
    issues: [],
    warnings,
    derived: {
      ...raw,
      avg_daily_calories: number(raw.avg_daily_calories),
      estimated_plan_cost: number(raw.estimated_plan_cost),
      target_calorie_range: Array.isArray(raw.target_calorie_range) ? raw.target_calorie_range : [],
      quality_metrics: { max_recipe_repeat: number(raw.max_recipe_repeats) },
    },
  }
}

function legacyGenerationMeta(value: unknown, plan: WeeklyDay[]): GenerationMeta {
  const raw = object(value)
  const uniqueNames = new Set(
    plan.flatMap(day => Object.values(day.meals)).filter(Boolean).map(meal => meal!.name),
  )
  return {
    strategy: String(raw.strategy || 'legacy_database_recommendation'),
    rag_enabled: Boolean(raw.rag_enabled),
    rag_used: Boolean(raw.rag_used),
    fallback_used: Boolean(raw.fallback_used),
    weight_version: raw.weight_version ? String(raw.weight_version) : undefined,
    rag_sources: [],
    rag_error: null,
    repair_attempts: 0,
    estimate_source: 'legacy_estimate',
    candidate_count: number(raw.candidate_count),
    unique_recipe_count: uniqueNames.size,
    max_recipe_repeat: 0,
  }
}

/** Convert persisted V1 snapshots into the stable result-page contract. */
export function normalizePlanResult(value: unknown): PlanResult | null {
  const raw = object(value)
  if (!Object.keys(raw).length) return null
  if (raw.schema_version === 'ai_native_v2' && Array.isArray(raw.recipes)) {
    return raw as PlanResult
  }

  const plan = weeklyPlan(raw.weekly_plan)
  return {
    schema_version: 'legacy_v1',
    recipes: Array.isArray(raw.top5) ? raw.top5 as TopRecipe[] : [],
    weekly_plan: plan,
    nutrition_report: nutritionReport(raw.nutrition_report),
    shopping_list: shoppingList(raw.shopping_list),
    validation: legacyValidation(raw.plan_validation),
    generation_meta: legacyGenerationMeta(raw.recommendation_meta, plan),
    summary: String(raw.summary || '历史方案已加载。'),
  }
}
