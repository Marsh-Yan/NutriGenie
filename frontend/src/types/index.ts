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
  run_id: number | null
  run_status: string | null
  current_node: string | null
  current_version_id: number | null
  has_current_version: boolean
  progress: ProgressInfo | null
  error: string | null
  last_error: string | null
  created_at: string
  completed_at: string | null
}

export interface PlanMessageRequest {
  message?: string
  action?: Record<string, any>
  client_request_id?: string
}

export interface PlanRun {
  run_id: number
  plan_id: number
  status: PlanStatus
  current_node?: string | null
  base_version_id?: number | null
  output_version_id?: number | null
  error?: string | null
}

export interface PlanMessage {
  message_id: number
  plan_id: number
  version_id: number | null
  role: 'user' | 'assistant' | string
  content: string
  action?: Record<string, any> | null
  status: string
  created_at: string
}

export interface PlanVersionSummary {
  version_id: number
  version_no: number
  parent_version_id: number | null
  validation: PlanValidation | Record<string, any> | null
  created_at: string
  is_current: boolean
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
  schema_version: string
  version_id?: number
  version_no?: number
  recipes: GeneratedRecipe[]
  weekly_plan: WeeklyDay[]
  nutrition_report: NutritionReport
  shopping_list: ShoppingList
  validation: PlanValidation
  generation_meta: GenerationMeta
  summary: string
}

export interface GeneratedNutrition {
  calories: number
  protein_g: number
  fat_g: number
  carbs_g: number
  fiber_g: number
}

export interface PlanValidation {
  status: 'passed' | 'warning' | 'failed' | string
  passed: boolean
  issues: { code: string; message: string; severity: 'error' | 'warning'; path?: string | null }[]
  derived: Record<string, any>
  warnings: string[]
}

export interface GenerationMeta {
  strategy: string
  rag_enabled: boolean
  rag_used: boolean
  rag_sources: { chunk_id: string; source_file?: string | null; section_title?: string | null; score: number }[]
  rag_error?: string | null
  repair_attempts: number
  estimate_source: string
  intent_snapshot?: Record<string, any>
  constraints_snapshot?: Record<string, any>
}

export interface GeneratedIngredient {
  name: string
  quantity: number
  unit: string
  optional: boolean
  nutrition_estimate: GeneratedNutrition
  line_cost_estimate: number
}

export interface GeneratedRecipe {
  recipe_key: string
  source: string
  name: string
  category: string
  cuisine_type: string
  difficulty: string
  prep_time_min: number
  cook_time_min: number
  servings: number
  ingredients: GeneratedIngredient[]
  steps: string[]
  nutrition: GeneratedNutrition
  nutrition_estimate?: GeneratedNutrition
  declared_nutrition?: GeneratedNutrition
  estimated_cost: number
  cost_estimate?: number
  declared_cost?: number
  estimate_source: string
  generation_note: string
}

// Legacy display type retained by the read-only demo page.
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
  meals: Record<string, MealItem | null>
  total_nutrition: GeneratedNutrition
}

export interface DayMeals {
  breakfast: MealItem | null
  lunch: MealItem | null
  dinner: MealItem | null
}

export interface MealItem {
  recipe_key?: string
  recipe_id?: number
  name: string
  serving_size: number
  nutrition: MealNutrition | GeneratedNutrition
}

export interface MealNutrition {
  calories: number
  protein?: number
  fat?: number
  carbs?: number
  protein_g?: number
  fat_g?: number
  carbs_g?: number
  fiber_g?: number
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
  ingredient_id?: number
  name: string
  quantity: number
  unit: string
  estimated_cost: number
  for_recipes: { recipe_key?: string; recipe_id?: number; name: string }[]
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
