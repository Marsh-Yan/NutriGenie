import api from './index'

export interface AdminOverview {
  users: number
  profiles: number
  recipes: number
  ingredients: number
  plans: number
}

export async function getOverview(): Promise<AdminOverview> {
  const { data } = await api.get('/admin/overview')
  return data
}

export interface AdminIngredient {
  ingredient_id: number
  name: string
  category: string
  unit: string
  unit_price: number
  season_tags: string[] | null
  storage_days: number
  nutrition: { calories: number; protein: number; fat: number; carbs: number; fiber: number }
}

export type AdminIngredientInput = Omit<AdminIngredient, 'ingredient_id'>

export async function listIngredients(): Promise<AdminIngredient[]> {
  const { data } = await api.get('/admin/ingredients')
  return data
}

export async function createIngredient(input: AdminIngredientInput): Promise<AdminIngredient> {
  const { data } = await api.post('/admin/ingredients', input)
  return data
}

export async function updateIngredient(id: number, input: AdminIngredientInput): Promise<AdminIngredient> {
  const { data } = await api.put(`/admin/ingredients/${id}`, input)
  return data
}

export async function deleteIngredient(id: number): Promise<void> {
  await api.delete(`/admin/ingredients/${id}`)
}

export interface AdminRecipeInput {
  name: string; description?: string | null; category: string; cuisine_type: string; difficulty: 'easy' | 'medium' | 'hard'
  prep_time: number; cook_time: number; servings: number; steps: { step: number; content: string }[]; image_url?: string | null
  nutrition: { calories: number; protein: number; fat: number; carbs: number; fiber: number }
  tags?: string[] | null; ingredients: { ingredient_id: number; quantity: number; unit: string; is_optional: boolean }[]
}
export async function createRecipe(input: AdminRecipeInput): Promise<{ recipe_id: number }> { const { data } = await api.post('/admin/recipes', input); return data }
export async function updateRecipe(id: number, input: AdminRecipeInput): Promise<{ recipe_id: number }> { const { data } = await api.put(`/admin/recipes/${id}`, input); return data }
export async function deleteRecipe(id: number): Promise<void> { await api.delete(`/admin/recipes/${id}`) }
export async function listRecipes(): Promise<{ items: any[] }> { const { data } = await api.get('/recipes', { params: { page_size: 50 } }); return data }
export async function getRecipeDetail(id: number): Promise<any> { const { data } = await api.get(`/recipes/${id}`); return data }

export interface KnowledgeDocument { recipe_id: number; source_file: string; content_hash: string; preview: string }
export async function listKnowledgeDocuments(): Promise<KnowledgeDocument[]> { const { data } = await api.get('/admin/knowledge/documents'); return data }
export async function getKnowledgeDocument(id: number): Promise<{ recipe_id: number; content: string }> { const { data } = await api.get(`/admin/knowledge/documents/${id}`); return data }
export async function saveKnowledgeDocument(id: number, content: string): Promise<void> { await api.put(`/admin/knowledge/documents/${id}`, { recipe_id: id, content }) }
export async function rebuildKnowledgeIndex(): Promise<{ indexed_documents: number }> { const { data } = await api.post('/admin/knowledge/rebuild'); return data }
export async function uploadKnowledgeDocument(file: File): Promise<{ recipe_id: number; source_file: string; reindex_required: boolean }> {
  const form = new FormData(); form.append('file', file)
  const { data } = await api.post('/admin/knowledge/upload', form, { headers: { 'Content-Type': 'multipart/form-data' } })
  return data
}
