/* ═══════════════════════════════════════════
   NutriGenie — TypeScript Type Definitions
   ═══════════════════════════════════════════ */

// ── 用户画像 ─────────────────────────────

export interface Profile {
  profile_id: number
  age: number
  gender: 'male' | 'female'
  height: number
  weight: number
  activity_level: ActivityLevel
  diet_type: DietType
  health_goal: HealthGoal
  allergies: string[] | null
  daily_budget: number
  tdee?: number
  bmi?: number
  created_at: string
  updated_at?: string
}

export type UserRole = 'user' | 'admin'
export interface AuthUser { user_id: number; email: string; nickname: string; role: UserRole; is_active: boolean; created_at: string }
export interface AuthResponse { access_token: string; token_type: 'bearer'; expires_in: number; user: AuthUser }

export type DietType = 'balanced' | 'keto' | 'high_protein' | 'gluten_free' | 'vegan' | 'healthy'
export type HealthGoal = 'fat_loss' | 'muscle_gain' | 'blood_sugar' | 'healthy'
export type ActivityLevel = 'sedentary' | 'light' | 'moderate' | 'active' | 'extra'

export interface ProfileFormData {
  age: number | null
  gender: 'male' | 'female' | null
  height: number | null
  weight: number | null
  activity_level: ActivityLevel
  diet_type: DietType
  health_goal: HealthGoal
  allergies: string[]
  daily_budget: number | null
}

// ── 菜谱 ─────────────────────────────────

export interface RecipeListItem {
  recipe_id: number
  name: string
  category: string
  cuisine_type: string
  difficulty: string
  prep_time: number
  cook_time: number
  image_url: string | null
  total_calories: number
  tags: string[] | null
}

export interface RecipeDetail extends RecipeListItem {
  description: string
  servings: number
  steps: RecipeStep[]
  ingredients: RecipeIngredientItem[]
  nutrition: NutritionData | null
  estimated_cost: number
}

export interface RecipeStep {
  step: number
  content: string
}

export interface RecipeIngredientItem {
  ingredient_id: number
  name: string
  quantity: number
  unit: string
  is_optional: boolean
}

export interface NutritionData {
  calories: number
  protein: number
  fat: number
  carbs: number
  fiber: number
}

// ── 规划 ─────────────────────────────────

export interface PlanCreateRequest {
  profile_id: number
  user_input: string
  duration_days: number
  total_budget: number
}

export interface PlanCreateResponse {
  plan_id: number
  status: PlanStatus
  created_at: string
  links: {
    status: string
    result: string
  }
}

export interface PlanListItem {
  plan_id: number
  status: PlanStatus
  user_input: string
  duration_days: number
  total_budget: number
  created_at: string
  completed_at: string | null
}

export type PlanStatus = 'pending' | 'running' | 'completed' | 'failed'

export interface PlanStatusResponse {
  plan_id: number
  status: PlanStatus
  current_node: string | null
  progress: ProgressInfo | null
  error: string | null
  created_at: string
  completed_at: string | null
}

export interface ProgressInfo {
  total_steps: number
  completed_steps: number
  current_step: number
  step_name: string
  steps: StepItem[]
}

export interface StepItem {
  name: string
  status: 'completed' | 'running' | 'pending'
  order: number
}

export interface PlanResultResponse {
  plan_id: number
  status: PlanStatus
  profile_id: number
  user_input: string
  created_at: string
  completed_at: string | null
  result: PlanResult | null
}

export interface PlanResult {
  top5: TopRecipe[]
  weekly_plan: WeeklyDay[]
  nutrition_report: NutritionReport
  shopping_list: ShoppingList
  recommendation_meta?: RecommendationMeta
  plan_validation?: PlanValidation
  summary: string
}

export interface RecommendationMeta {
  strategy: string
  rag_enabled: boolean
  rag_used: boolean
  fallback_used: boolean
  candidate_count: number
  weight_version: string
}

export interface PlanValidation {
  passed: boolean
  missing_meals: { day: number; meal_slot: string }[]
  avg_daily_calories: number
  target_calorie_range: number[]
  estimated_plan_cost: number
  estimated_procurement_cost?: number
  budget_target_range?: number[]
  total_budget: number
  max_recipe_repeats: number
  warnings: string[]
}

export interface TopRecipe {
  recipe_id: number
  name: string
  image_url: string | null
  category: string
  cuisine_type: string
  difficulty: string
  prep_time: number
  cook_time: number
  scores: SixScores
  total_score: number
  nutrition: NutritionData
  estimated_cost: number
  explanation: string
  evidence?: RecommendationEvidence
}

export interface SixScores {
  health: number
  budget: number
  preference: number
  season: number
  variety: number
  utilization: number
  semantic?: number
}

export interface RecommendationEvidence {
  matched_preferences: string[]
  objective_evidence: { type: string; actual: number; target_range?: number[]; daily_budget?: number }[]
  retrieval_sources: string[]
  warnings: string[]
}

export interface WeeklyDay {
  day: number
  meals: DayMeals
  total_nutrition: MealNutrition
}

export interface DayMeals {
  breakfast: MealItem | null
  lunch: MealItem | null
  dinner: MealItem | null
}

export interface MealItem {
  recipe_id: number
  name: string
  serving_size: number
  nutrition: MealNutrition
}

export interface MealNutrition {
  calories: number
  protein: number
  fat: number
  carbs: number
}

export interface NutritionReport {
  avg_daily_calories: number
  total_calories: number
  protein_g: number
  fat_g: number
  carbs_g: number
  fiber_g: number
  protein_pct: number
  fat_pct: number
  carbs_pct: number
  recommendation: string
}

export interface ShoppingList {
  total_cost: number
  items: ShoppingItem[]
  by_category: Record<string, ShoppingCategoryItem[]>
}

export interface ShoppingItem {
  ingredient_id: number
  name: string
  quantity: number
  unit: string
  estimated_cost: number
  for_recipes: { recipe_id: number; name: string }[]
}

export interface ShoppingCategoryItem {
  name: string
  quantity: number
  unit: string
  estimated_cost: number
}

// ── 食材 ─────────────────────────────────

export interface IngredientItem {
  ingredient_id: number
  name: string
  category: string
  unit: string
  unit_price: number
  season_tags: string[] | null
  nutrition_per_100g: NutritionData | null
}
