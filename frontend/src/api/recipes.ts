import api from './index'
import type { RecipeListItem, RecipeDetail } from '@/types'

export interface RecipeListParams {
  category?: string
  cuisine_type?: string
  difficulty?: string
  max_prep_time?: number
  tags?: string
  page?: number
  page_size?: number
}

export interface RecipeListResponse {
  total: number
  page: number
  page_size: number
  items: RecipeListItem[]
}

export async function getRecipes(params?: RecipeListParams): Promise<RecipeListResponse> {
  const { data } = await api.get('/recipes', { params })
  return {
    total: Number(data?.total) || 0,
    page: Number(data?.page) || 1,
    page_size: Number(data?.page_size) || 20,
    items: Array.isArray(data?.items) ? data.items.map((item: RecipeListItem) => ({
      ...item,
      recipe_id: Number(item.recipe_id),
      prep_time: Number(item.prep_time) || 0,
      cook_time: Number(item.cook_time) || 0,
      total_calories: Number(item.total_calories) || 0,
      tags: Array.isArray(item.tags) ? item.tags.map(String) : [],
    })) : [],
  }
}

export async function getRecipeDetail(id: number): Promise<RecipeDetail> {
  const { data } = await api.get(`/recipes/${id}`)
  return {
    ...data,
    recipe_id: Number(data.recipe_id),
    description: String(data.description || ''),
    prep_time: Number(data.prep_time) || 0,
    cook_time: Number(data.cook_time) || 0,
    servings: Math.max(1, Number(data.servings) || 1),
    total_calories: Number(data.total_calories ?? data.nutrition?.calories) || 0,
    estimated_cost: Number(data.estimated_cost) || 0,
    tags: Array.isArray(data.tags) ? data.tags.map(String) : [],
    steps: Array.isArray(data.steps) ? data.steps.map((step: { step?: unknown; content?: unknown }, index: number) => ({
      step: Number(step.step) || index + 1,
      content: String(step.content || ''),
    })) : [],
    ingredients: Array.isArray(data.ingredients) ? data.ingredients.map((item: RecipeDetail['ingredients'][number]) => ({
      ...item,
      ingredient_id: Number(item.ingredient_id),
      quantity: Number(item.quantity) || 0,
      is_optional: Boolean(item.is_optional),
    })) : [],
    nutrition: data.nutrition ? {
      calories: Number(data.nutrition.calories) || 0,
      protein: Number(data.nutrition.protein) || 0,
      fat: Number(data.nutrition.fat) || 0,
      carbs: Number(data.nutrition.carbs) || 0,
      fiber: Number(data.nutrition.fiber) || 0,
    } : null,
  }
}
