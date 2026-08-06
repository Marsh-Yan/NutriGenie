import api from './index'
import type { RecipeListItem, RecipeDetail } from '@/types'

export interface RecipeListParams {
  category?: string
  cuisine_type?: string
  difficulty?: string
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
  return data
}

export async function getRecipeDetail(id: number): Promise<RecipeDetail> {
  const { data } = await api.get(`/recipes/${id}`)
  return data
}
