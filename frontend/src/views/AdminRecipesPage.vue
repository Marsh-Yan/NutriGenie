<script setup lang="ts">
import { nextTick, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import {
  createRecipe,
  deleteRecipe,
  getRecipeDetail,
  listIngredients,
  listRecipes,
  updateRecipe,
  type AdminIngredient,
  type AdminRecipeInput,
  type AdminRecipeSummary,
} from '@/api/admin'

interface EditorStep {
  key: number
  content: string
}

interface EditorIngredient {
  key: number
  ingredient_id: number | null
  quantity: number
  unit: string
  is_optional: boolean
}

interface RecipeFormState {
  name: string
  description: string
  category: string
  cuisine_type: string
  difficulty: AdminRecipeInput['difficulty']
  prep_time: number
  cook_time: number
  servings: number
  image_url: string
  tags: string[]
  nutrition: AdminRecipeInput['nutrition']
  steps: EditorStep[]
  ingredients: EditorIngredient[]
}

const categoryOptions = [
  { value: 'main_dish', label: '主菜' },
  { value: 'side_dish', label: '配菜' },
  { value: 'soup', label: '汤羹' },
  { value: 'staple', label: '主食' },
  { value: 'light_meal', label: '轻食' },
]
const cuisineOptions = [
  { value: 'chinese', label: '中式' },
  { value: 'western', label: '西式' },
]
const difficultyOptions = [
  { value: 'easy', label: '简单' },
  { value: 'medium', label: '适中' },
  { value: 'hard', label: '较难' },
]

const recipes = ref<AdminRecipeSummary[]>([])
const ingredientOptions = ref<AdminIngredient[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = 20
const loading = ref(false)
const pageError = ref('')
const editorVisible = ref(false)
const detailLoadingId = ref<number | null>(null)
const saving = ref(false)
const activeId = ref<number | null>(null)
const formRef = ref<FormInstance>()
let editorKey = 0

function nextKey() {
  editorKey += 1
  return editorKey
}

function emptyForm(): RecipeFormState {
  return {
    name: '',
    description: '',
    category: 'main_dish',
    cuisine_type: 'chinese',
    difficulty: 'medium',
    prep_time: 10,
    cook_time: 20,
    servings: 1,
    image_url: '',
    tags: [],
    nutrition: { calories: 0, protein: 0, fat: 0, carbs: 0, fiber: 0 },
    steps: [{ key: nextKey(), content: '' }],
    ingredients: [{ key: nextKey(), ingredient_id: null, quantity: 100, unit: 'g', is_optional: false }],
  }
}

const form = reactive<RecipeFormState>(emptyForm())
const rules: FormRules<RecipeFormState> = {
  name: [{ required: true, message: '请填写菜谱名称', trigger: 'blur' }],
  category: [{ required: true, message: '请选择菜谱类型', trigger: 'change' }],
  cuisine_type: [{ required: true, message: '请选择菜系', trigger: 'change' }],
  difficulty: [{ required: true, message: '请选择难度', trigger: 'change' }],
}

function replaceForm(next: RecipeFormState) {
  Object.assign(form, next)
}

async function loadRecipes() {
  loading.value = true
  pageError.value = ''
  try {
    const response = await listRecipes(page.value, pageSize)
    recipes.value = response.items
    total.value = response.total
  } catch (cause) {
    pageError.value = cause instanceof Error ? cause.message : '菜谱列表加载失败'
  } finally {
    loading.value = false
  }
}

async function loadIngredientOptions() {
  try {
    ingredientOptions.value = await listIngredients()
  } catch (cause) {
    ElMessage.error(cause instanceof Error ? cause.message : '食材选项加载失败')
  }
}

async function openCreate() {
  activeId.value = null
  replaceForm(emptyForm())
  editorVisible.value = true
  await nextTick()
  formRef.value?.clearValidate()
}

async function openEdit(row: AdminRecipeSummary) {
  detailLoadingId.value = row.recipe_id
  try {
    const detail = await getRecipeDetail(row.recipe_id)
    activeId.value = row.recipe_id
    replaceForm({
      name: detail.name,
      description: detail.description || '',
      category: detail.category,
      cuisine_type: detail.cuisine_type,
      difficulty: detail.difficulty,
      prep_time: detail.prep_time,
      cook_time: detail.cook_time,
      servings: detail.servings,
      image_url: detail.image_url || '',
      tags: detail.tags || [],
      nutrition: { ...detail.nutrition },
      steps: detail.steps.map((item) => ({ key: nextKey(), content: item.content })),
      ingredients: detail.ingredients.map((item) => ({
        key: nextKey(),
        ingredient_id: item.ingredient_id,
        quantity: item.quantity,
        unit: item.unit,
        is_optional: item.is_optional,
      })),
    })
    editorVisible.value = true
    await nextTick()
    formRef.value?.clearValidate()
  } catch (cause) {
    ElMessage.error(cause instanceof Error ? cause.message : '菜谱详情加载失败')
  } finally {
    detailLoadingId.value = null
  }
}

function addStep() {
  form.steps.push({ key: nextKey(), content: '' })
}

function removeStep(key: number) {
  if (form.steps.length === 1) return
  form.steps = form.steps.filter((item) => item.key !== key)
}

function addIngredient() {
  form.ingredients.push({ key: nextKey(), ingredient_id: null, quantity: 100, unit: 'g', is_optional: false })
}

function removeIngredient(key: number) {
  if (form.ingredients.length === 1) return
  form.ingredients = form.ingredients.filter((item) => item.key !== key)
}

function syncIngredientUnit(index: number) {
  const selected = ingredientOptions.value.find((item) => item.ingredient_id === form.ingredients[index].ingredient_id)
  if (selected) form.ingredients[index].unit = selected.unit
}

function toPayload(): AdminRecipeInput | null {
  const ingredientIds = form.ingredients.map((item) => item.ingredient_id)
  if (ingredientIds.some((id) => id === null)) {
    ElMessage.warning('请为每一项用料选择食材')
    return null
  }
  if (new Set(ingredientIds).size !== ingredientIds.length) {
    ElMessage.warning('同一种食材不能重复添加，请合并用量')
    return null
  }

  return {
    name: form.name.trim(),
    description: form.description.trim() || null,
    category: form.category,
    cuisine_type: form.cuisine_type,
    difficulty: form.difficulty,
    prep_time: form.prep_time,
    cook_time: form.cook_time,
    servings: form.servings,
    steps: form.steps.map((item, index) => ({ step: index + 1, content: item.content.trim() })),
    image_url: form.image_url.trim() || null,
    nutrition: { ...form.nutrition },
    tags: form.tags.length ? form.tags : null,
    ingredients: form.ingredients.map((item) => ({
      ingredient_id: Number(item.ingredient_id),
      quantity: item.quantity,
      unit: item.unit.trim(),
      is_optional: item.is_optional,
    })),
  }
}

async function save() {
  try {
    await formRef.value?.validate()
  } catch {
    return
  }
  const payload = toPayload()
  if (!payload) return

  saving.value = true
  try {
    if (activeId.value) await updateRecipe(activeId.value, payload)
    else {
      await createRecipe(payload)
      page.value = 1
    }
    ElMessage.success(activeId.value ? '菜谱已更新' : '菜谱已创建')
    editorVisible.value = false
    await loadRecipes()
  } catch (cause) {
    ElMessage.error(cause instanceof Error ? cause.message : '菜谱保存失败')
  } finally {
    saving.value = false
  }
}

async function remove(row: AdminRecipeSummary) {
  try {
    await ElMessageBox.confirm(
      `删除后标准菜谱库将不再显示「${row.name}」，此操作无法撤销。`,
      '确认删除菜谱？',
      { type: 'warning', confirmButtonText: '确认删除', cancelButtonText: '保留菜谱' },
    )
    await deleteRecipe(row.recipe_id)
    ElMessage.success('菜谱已删除')
    if (recipes.value.length === 1 && page.value > 1) page.value -= 1
    await loadRecipes()
  } catch (cause) {
    if (cause !== 'cancel' && cause !== 'close') {
      ElMessage.error(cause instanceof Error ? cause.message : '菜谱删除失败')
    }
  }
}

async function changePage(nextPage: number) {
  page.value = nextPage
  await loadRecipes()
}

onMounted(() => Promise.all([loadRecipes(), loadIngredientOptions()]))
</script>

<template>
  <div class="page-container recipe-admin">
    <header class="top">
      <div>
        <span class="eyebrow">标准数据</span>
        <h1>菜谱库维护</h1>
        <p>维护确定性的食材、营养与步骤数据，保存后立即用于标准菜谱库。</p>
      </div>
      <el-button type="primary" @click="openCreate">新增菜谱</el-button>
    </header>

    <el-alert
      v-if="pageError"
      :title="pageError"
      type="error"
      :closable="false"
      show-icon
    >
      <template #default><el-button link type="primary" @click="loadRecipes">重新加载</el-button></template>
    </el-alert>

    <section v-else class="table-shell card" aria-labelledby="recipe-table-title">
      <div class="table-heading">
        <div><h2 id="recipe-table-title">已收录菜谱</h2><p>共 {{ total }} 道标准菜谱</p></div>
      </div>
      <el-table v-loading="loading" :data="recipes" empty-text="还没有菜谱，请先新增一条">
        <el-table-column prop="name" label="菜谱" min-width="180" />
        <el-table-column label="类型" width="110">
          <template #default="{ row }">{{ categoryOptions.find((item) => item.value === row.category)?.label || row.category }}</template>
        </el-table-column>
        <el-table-column label="难度" width="100">
          <template #default="{ row }">{{ difficultyOptions.find((item) => item.value === row.difficulty)?.label || row.difficulty }}</template>
        </el-table-column>
        <el-table-column label="耗时" width="110">
          <template #default="{ row }">{{ row.prep_time + row.cook_time }} 分钟</template>
        </el-table-column>
        <el-table-column label="操作" width="170" fixed="right">
          <template #default="{ row }">
            <div class="row-actions">
              <el-button link type="primary" :loading="detailLoadingId === row.recipe_id" @click="openEdit(row)">编辑</el-button>
              <el-button link type="danger" @click="remove(row)">删除</el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination
        v-if="total > pageSize"
        class="pagination"
        background
        layout="prev, pager, next"
        :current-page="page"
        :page-size="pageSize"
        :total="total"
        @current-change="changePage"
      />
    </section>

    <el-dialog
      v-model="editorVisible"
      class="recipe-editor-dialog"
      :title="activeId ? '编辑菜谱' : '新增菜谱'"
      width="860px"
      :close-on-click-modal="false"
      destroy-on-close
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top" scroll-to-error>
        <section class="form-section" aria-labelledby="basic-section-title">
          <div class="form-section__heading"><h3 id="basic-section-title">基础信息</h3><p>名称、分类和时间会直接展示给用户。</p></div>
          <div class="form-grid form-grid--three">
            <el-form-item label="菜谱名称" prop="name"><el-input v-model="form.name" maxlength="100" show-word-limit /></el-form-item>
            <el-form-item label="菜谱类型" prop="category"><el-select v-model="form.category"><el-option v-for="item in categoryOptions" :key="item.value" :label="item.label" :value="item.value" /></el-select></el-form-item>
            <el-form-item label="菜系" prop="cuisine_type"><el-select v-model="form.cuisine_type"><el-option v-for="item in cuisineOptions" :key="item.value" :label="item.label" :value="item.value" /></el-select></el-form-item>
            <el-form-item label="难度" prop="difficulty"><el-select v-model="form.difficulty"><el-option v-for="item in difficultyOptions" :key="item.value" :label="item.label" :value="item.value" /></el-select></el-form-item>
            <el-form-item label="准备时间（分钟）"><el-input-number v-model="form.prep_time" :min="0" :max="1440" controls-position="right" /></el-form-item>
            <el-form-item label="烹饪时间（分钟）"><el-input-number v-model="form.cook_time" :min="0" :max="1440" controls-position="right" /></el-form-item>
            <el-form-item label="份数"><el-input-number v-model="form.servings" :min="1" :max="20" controls-position="right" /></el-form-item>
            <el-form-item label="标签"><el-select v-model="form.tags" multiple filterable allow-create default-first-option placeholder="输入后回车添加" /></el-form-item>
            <el-form-item label="图片地址（可选）"><el-input v-model="form.image_url" type="url" placeholder="https://…" /></el-form-item>
          </div>
          <el-form-item label="菜谱说明（可选）"><el-input v-model="form.description" type="textarea" :rows="3" maxlength="1000" show-word-limit /></el-form-item>
        </section>

        <section class="form-section" aria-labelledby="ingredient-section-title">
          <div class="form-section__heading form-section__heading--action">
            <div><h3 id="ingredient-section-title">用料</h3><p>只能选择食材库中的标准食材，同一食材不能重复。</p></div>
            <el-button plain @click="addIngredient">添加用料</el-button>
          </div>
          <div class="editor-list">
            <div v-for="(item, index) in form.ingredients" :key="item.key" class="ingredient-row">
              <el-form-item
                :label="`食材 ${index + 1}`"
                :prop="`ingredients.${index}.ingredient_id`"
                :rules="[{ required: true, message: '请选择食材', trigger: 'change' }]"
              >
                <el-select v-model="item.ingredient_id" filterable placeholder="搜索食材" @change="syncIngredientUnit(index)">
                  <el-option v-for="option in ingredientOptions" :key="option.ingredient_id" :label="`${option.name} · #${option.ingredient_id}`" :value="option.ingredient_id" />
                </el-select>
              </el-form-item>
              <el-form-item label="用量"><el-input-number v-model="item.quantity" :min="0.01" :precision="2" controls-position="right" /></el-form-item>
              <el-form-item label="单位"><el-input v-model="item.unit" maxlength="20" /></el-form-item>
              <el-form-item label="可选"><el-switch v-model="item.is_optional" aria-label="标记为可选食材" /></el-form-item>
              <el-button class="remove-button" plain type="danger" :disabled="form.ingredients.length === 1" @click="removeIngredient(item.key)">移除</el-button>
            </div>
          </div>
        </section>

        <section class="form-section" aria-labelledby="steps-section-title">
          <div class="form-section__heading form-section__heading--action">
            <div><h3 id="steps-section-title">制作步骤</h3><p>保存时会按当前顺序自动编号。</p></div>
            <el-button plain @click="addStep">添加步骤</el-button>
          </div>
          <div class="editor-list">
            <div v-for="(item, index) in form.steps" :key="item.key" class="step-row">
              <span class="step-number" aria-hidden="true">{{ index + 1 }}</span>
              <el-form-item
                :prop="`steps.${index}.content`"
                :rules="[{ required: true, message: '请填写步骤内容', trigger: 'blur' }]"
              >
                <el-input v-model="item.content" maxlength="500" show-word-limit placeholder="描述这一操作步骤" />
              </el-form-item>
              <el-button class="remove-button" plain type="danger" :disabled="form.steps.length === 1" @click="removeStep(item.key)">移除</el-button>
            </div>
          </div>
        </section>

        <section class="form-section" aria-labelledby="nutrition-section-title">
          <div class="form-section__heading"><h3 id="nutrition-section-title">每份营养</h3><p>填写确定性营养结果，不由模型自动推断。</p></div>
          <div class="nutrition-grid">
            <el-form-item label="热量 kcal"><el-input-number v-model="form.nutrition.calories" :min="0" :precision="1" controls-position="right" /></el-form-item>
            <el-form-item label="蛋白质 g"><el-input-number v-model="form.nutrition.protein" :min="0" :precision="1" controls-position="right" /></el-form-item>
            <el-form-item label="脂肪 g"><el-input-number v-model="form.nutrition.fat" :min="0" :precision="1" controls-position="right" /></el-form-item>
            <el-form-item label="碳水 g"><el-input-number v-model="form.nutrition.carbs" :min="0" :precision="1" controls-position="right" /></el-form-item>
            <el-form-item label="膳食纤维 g"><el-input-number v-model="form.nutrition.fiber" :min="0" :precision="1" controls-position="right" /></el-form-item>
          </div>
        </section>
      </el-form>

      <template #footer>
        <el-button :disabled="saving" @click="editorVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">{{ activeId ? '保存修改' : '创建菜谱' }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped lang="scss">
.recipe-admin { max-width: 1200px; padding-top: 44px; padding-bottom: 88px; }
.top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  margin-bottom: 18px;
  padding: 30px;
  border: 1px solid rgba($color-sage-dark, .1);
  border-radius: $radius-xl;
  background: linear-gradient(135deg, $color-surface-soft, $color-blue-soft);
}
.eyebrow { color: $color-sage-dark; font-size: 12px; font-weight: 800; letter-spacing: .12em; text-transform: uppercase; }
.top h1 { margin: 6px 0; font-size: clamp(28px, 4vw, 40px); letter-spacing: -.04em; }
.top p,
.table-heading p,
.form-section__heading p { margin: 0; color: $color-text-secondary; line-height: 1.6; }
.top :deep(.el-button) { min-height: 44px; }
.el-alert { margin-bottom: 16px; border-radius: $radius-md; }
.table-shell { overflow: hidden; padding: 0; box-shadow: $shadow-sm; }
.table-heading { padding: 20px 24px 12px; }
.table-heading h2 { margin: 0 0 3px; font-size: 19px; }
.table-heading p { font-size: 13px; }
:deep(.el-table th.el-table__cell) { height: 52px; background: $color-surface-soft; color: $color-text-secondary; font-size: 12px; }
:deep(.el-table td.el-table__cell) { height: 58px; }
.row-actions { display: flex; gap: 4px; }
.row-actions :deep(.el-button) { min-width: 48px; min-height: 40px; margin: 0; }
.pagination { justify-content: flex-end; padding: 18px 24px 22px; }

.form-section { padding: 4px 0 24px; }
.form-section + .form-section { padding-top: 24px; border-top: 1px solid $color-border; }
.form-section__heading { margin-bottom: 16px; }
.form-section__heading h3 { margin: 0 0 4px; color: $color-text-primary; font-size: 18px; }
.form-section__heading p { font-size: 13px; }
.form-section__heading--action { display: flex; align-items: center; justify-content: space-between; gap: 16px; }
.form-section__heading--action :deep(.el-button) { min-height: 40px; }
.form-grid { display: grid; gap: 0 16px; }
.form-grid--three { grid-template-columns: repeat(3, minmax(0, 1fr)); }
.form-grid :deep(.el-select),
.form-grid :deep(.el-input-number),
.nutrition-grid :deep(.el-input-number),
.ingredient-row :deep(.el-select),
.ingredient-row :deep(.el-input-number) { width: 100%; }
.editor-list { display: grid; gap: 12px; }
.ingredient-row {
  display: grid;
  grid-template-columns: minmax(180px, 1.5fr) minmax(120px, .75fr) minmax(90px, .55fr) 64px auto;
  align-items: end;
  gap: 10px;
  padding: 14px;
  border: 1px solid $color-border;
  border-radius: $radius-md;
  background: $color-surface-soft;
}
.ingredient-row :deep(.el-form-item),
.step-row :deep(.el-form-item) { margin-bottom: 0; }
.step-row { display: grid; grid-template-columns: 34px minmax(0, 1fr) auto; align-items: center; gap: 10px; }
.step-number { display: grid; width: 32px; height: 32px; place-items: center; border-radius: 50%; background: $color-sage-light; color: $color-brand; font-family: $font-numeric; font-weight: 800; }
.remove-button { min-height: 40px; margin-bottom: 0; }
.nutrition-grid { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 14px; }

:global(.recipe-editor-dialog) { max-width: calc(100vw - 32px); border-radius: $radius-lg; }
:global(.recipe-editor-dialog .el-dialog__body) { max-height: min(68vh, 720px); overflow-y: auto; }
:global(.recipe-editor-dialog .el-dialog__footer .el-button) { min-height: 44px; }

@media (max-width: $breakpoint-lg) {
  .form-grid--three { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .nutrition-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
  .ingredient-row { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .ingredient-row .remove-button { justify-self: start; }
}

@media (max-width: $breakpoint-sm) {
  .recipe-admin { padding-top: 24px; }
  .top { align-items: stretch; flex-direction: column; padding: 24px 20px; }
  .top :deep(.el-button) { width: 100%; }
  .table-shell { overflow-x: auto; }
  .table-shell :deep(.el-table) { min-width: 720px; }
  .form-grid--three,
  .nutrition-grid,
  .ingredient-row { grid-template-columns: 1fr; }
  .form-section__heading--action { align-items: stretch; flex-direction: column; }
  .form-section__heading--action :deep(.el-button) { width: 100%; margin: 0; }
  .step-row { grid-template-columns: 34px minmax(0, 1fr); align-items: start; }
  .step-row .remove-button { grid-column: 2; justify-self: start; }
  :global(.recipe-editor-dialog .el-dialog__body) { padding-inline: 16px; }
}

@media (prefers-reduced-motion: reduce) {
  :global(.recipe-editor-dialog),
  :global(.recipe-editor-dialog *) { scroll-behavior: auto; }
}
</style>
