<script setup lang="ts">
import { computed, nextTick, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import type { AdminIngredient, AdminIngredientInput } from '@/api/admin'
import { createIngredient, deleteIngredient, listIngredients, updateIngredient } from '@/api/admin'

const categoryOptions = [
  { value: 'vegetable', label: '蔬菜' },
  { value: 'meat', label: '肉类' },
  { value: 'seafood', label: '水产' },
  { value: 'dairy', label: '乳制品' },
  { value: 'grain', label: '谷物' },
  { value: 'fruit', label: '水果' },
  { value: 'condiment', label: '调味品' },
  { value: 'egg', label: '蛋类' },
  { value: 'other', label: '其他' },
]
const seasonOptions = ['春季', '夏季', '秋季', '冬季']

const items = ref<AdminIngredient[]>([])
const loading = ref(false)
const saving = ref(false)
const pageError = ref('')
const dialogVisible = ref(false)
const editingId = ref<number | null>(null)
const formRef = ref<FormInstance>()
const page = ref(1)
const pageSize = 25
const pagedItems = computed(() => {
  const start = (page.value - 1) * pageSize
  return items.value.slice(start, start + pageSize)
})

function emptyForm(): AdminIngredientInput {
  return {
    name: '',
    category: 'vegetable',
    unit: 'g',
    unit_price: 0,
    season_tags: null,
    storage_days: 7,
    nutrition: { calories: 0, protein: 0, fat: 0, carbs: 0, fiber: 0 },
  }
}

const form = reactive<AdminIngredientInput>(emptyForm())
const rules: FormRules<AdminIngredientInput> = {
  name: [{ required: true, message: '请填写食材名称', trigger: 'blur' }],
  category: [{ required: true, message: '请选择食材分类', trigger: 'change' }],
  unit: [{ required: true, message: '请填写采购单位', trigger: 'blur' }],
}

async function load() {
  loading.value = true
  pageError.value = ''
  try {
    items.value = await listIngredients()
  } catch (cause) {
    pageError.value = cause instanceof Error ? cause.message : '食材列表加载失败'
  } finally {
    loading.value = false
  }
}

async function openCreate() {
  editingId.value = null
  Object.assign(form, emptyForm())
  dialogVisible.value = true
  await nextTick()
  formRef.value?.clearValidate()
}

async function openEdit(item: AdminIngredient) {
  editingId.value = item.ingredient_id
  Object.assign(form, {
    name: item.name,
    category: item.category,
    unit: item.unit,
    unit_price: item.unit_price,
    season_tags: item.season_tags ? [...item.season_tags] : null,
    storage_days: item.storage_days,
    nutrition: { ...item.nutrition },
  })
  dialogVisible.value = true
  await nextTick()
  formRef.value?.clearValidate()
}

async function save() {
  try {
    await formRef.value?.validate()
  } catch {
    return
  }

  saving.value = true
  try {
    const payload: AdminIngredientInput = {
      ...form,
      name: form.name.trim(),
      unit: form.unit.trim(),
      season_tags: form.season_tags?.length ? form.season_tags : null,
      nutrition: { ...form.nutrition },
    }
    if (editingId.value) await updateIngredient(editingId.value, payload)
    else {
      await createIngredient(payload)
      page.value = 1
    }
    ElMessage.success(editingId.value ? '食材已更新' : '食材已创建')
    dialogVisible.value = false
    await load()
  } catch (cause) {
    ElMessage.error(cause instanceof Error ? cause.message : '食材保存失败')
  } finally {
    saving.value = false
  }
}

async function remove(item: AdminIngredient) {
  try {
    await ElMessageBox.confirm(
      `删除后不能恢复；如果「${item.name}」仍被菜谱引用，系统会拒绝删除。`,
      '确认删除食材？',
      { type: 'warning', confirmButtonText: '确认删除', cancelButtonText: '保留食材' },
    )
    await deleteIngredient(item.ingredient_id)
    ElMessage.success('食材已删除')
    if (pagedItems.value.length === 1 && page.value > 1) page.value -= 1
    await load()
  } catch (cause) {
    if (cause !== 'cancel' && cause !== 'close') {
      ElMessage.error(cause instanceof Error ? cause.message : '食材删除失败')
    }
  }
}

onMounted(load)
</script>

<template>
  <div class="page-container admin-ingredients">
    <header class="top">
      <div>
        <span class="eyebrow">标准数据</span>
        <h1>食材库维护</h1>
        <p>价格、单位和每 100g 营养数据会直接影响预算与方案计算。</p>
      </div>
      <el-button type="primary" @click="openCreate">新增食材</el-button>
    </header>

    <el-alert v-if="pageError" :title="pageError" type="error" :closable="false" show-icon>
      <template #default><el-button link type="primary" @click="load">重新加载</el-button></template>
    </el-alert>

    <section v-else class="table-shell card" aria-labelledby="ingredient-table-title">
      <div class="table-heading">
        <div><h2 id="ingredient-table-title">已收录食材</h2><p>共 {{ items.length }} 项标准食材</p></div>
      </div>
      <el-table class="desktop-table" v-loading="loading" :data="pagedItems" empty-text="还没有食材，请先新增一项">
        <el-table-column prop="ingredient_id" label="编号" width="80" />
        <el-table-column prop="name" label="食材" min-width="140" />
        <el-table-column label="分类" width="110">
          <template #default="{ row }">{{ categoryOptions.find((item) => item.value === row.category)?.label || row.category }}</template>
        </el-table-column>
        <el-table-column label="采购价格" width="150"><template #default="{ row }">¥{{ row.unit_price }}/{{ row.unit }}</template></el-table-column>
        <el-table-column label="热量 / 100g" width="140"><template #default="{ row }">{{ row.nutrition.calories }} kcal</template></el-table-column>
        <el-table-column label="操作" width="170" fixed="right">
          <template #default="{ row }">
            <div class="row-actions">
              <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
              <el-button link type="danger" @click="remove(row)">删除</el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
      <ul v-loading="loading" class="mobile-data-list" aria-label="食材数据">
        <li v-for="item in pagedItems" :key="item.ingredient_id" class="mobile-data-card">
          <header><strong>{{ item.name }}</strong><span>#{{ item.ingredient_id }}</span></header>
          <dl>
            <div><dt>分类</dt><dd>{{ categoryOptions.find((option) => option.value === item.category)?.label || item.category }}</dd></div>
            <div><dt>采购价格</dt><dd>¥{{ item.unit_price }}/{{ item.unit }}</dd></div>
            <div><dt>热量</dt><dd>{{ item.nutrition.calories }} kcal / 100g</dd></div>
          </dl>
          <div class="mobile-card-actions">
            <el-button plain type="primary" @click="openEdit(item)">编辑</el-button>
            <el-button plain type="danger" @click="remove(item)">删除</el-button>
          </div>
        </li>
        <li v-if="!loading && !pagedItems.length" class="mobile-empty">还没有食材，请先新增一项</li>
      </ul>
      <el-pagination
        v-if="items.length > pageSize"
        class="pagination"
        background
        layout="prev, pager, next"
        :current-page="page"
        :page-size="pageSize"
        :total="items.length"
        @current-change="page = $event"
      />
    </section>

    <el-dialog
      v-model="dialogVisible"
      class="ingredient-editor-dialog"
      :title="editingId ? '编辑食材' : '新增食材'"
      width="680px"
      :close-on-click-modal="false"
      destroy-on-close
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top" scroll-to-error>
        <section class="form-section" aria-labelledby="ingredient-basic-title">
          <div class="form-section__heading"><h3 id="ingredient-basic-title">基础信息</h3><p>采购单位应与菜谱用量保持一致。</p></div>
          <div class="form-grid">
            <el-form-item label="食材名称" prop="name"><el-input v-model="form.name" maxlength="100" show-word-limit /></el-form-item>
            <el-form-item label="分类" prop="category"><el-select v-model="form.category"><el-option v-for="item in categoryOptions" :key="item.value" :label="item.label" :value="item.value" /></el-select></el-form-item>
            <el-form-item label="采购单位" prop="unit"><el-input v-model="form.unit" maxlength="20" placeholder="如 g、ml、个" /></el-form-item>
            <el-form-item label="单位价格（元）"><el-input-number v-model="form.unit_price" :min="0" :precision="2" controls-position="right" /></el-form-item>
            <el-form-item label="建议存放天数"><el-input-number v-model="form.storage_days" :min="0" :max="365" controls-position="right" /></el-form-item>
            <el-form-item label="适用季节（不选表示全年）"><el-select v-model="form.season_tags" multiple clearable><el-option v-for="season in seasonOptions" :key="season" :label="season" :value="season" /></el-select></el-form-item>
          </div>
        </section>

        <section class="form-section" aria-labelledby="ingredient-nutrition-title">
          <div class="form-section__heading"><h3 id="ingredient-nutrition-title">每 100g 营养</h3><p>所有数值均须为非负数。</p></div>
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
        <el-button :disabled="saving" @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">{{ editingId ? '保存修改' : '创建食材' }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped lang="scss">
.admin-ingredients { max-width: 1200px; padding-top: 44px; padding-bottom: 88px; }
.top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  margin-bottom: 18px;
  padding: 30px;
  border: 1px solid rgba($color-sage-dark, .1);
  border-radius: $radius-xl;
  background: linear-gradient(135deg, $color-surface-soft, rgba($color-lime-soft, .7));
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
.mobile-data-list { display: none; }
.pagination { justify-content: flex-end; padding: 18px 24px 22px; }
.form-section { padding: 4px 0 24px; }
.form-section + .form-section { padding-top: 24px; border-top: 1px solid $color-border; }
.form-section__heading { margin-bottom: 16px; }
.form-section__heading h3 { margin: 0 0 4px; color: $color-text-primary; font-size: 18px; }
.form-section__heading p { font-size: 13px; }
.form-grid,
.nutrition-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0 16px; }
.nutrition-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
.form-grid :deep(.el-select),
.form-grid :deep(.el-input-number),
.nutrition-grid :deep(.el-input-number) { width: 100%; }
:global(.ingredient-editor-dialog) { max-width: calc(100vw - 32px); border-radius: $radius-lg; }
:global(.ingredient-editor-dialog .el-dialog__body) { max-height: min(68vh, 720px); overflow-y: auto; }
:global(.ingredient-editor-dialog .el-dialog__footer .el-button) { min-height: 44px; }

@media (max-width: $breakpoint-sm) {
  .admin-ingredients { padding-top: 24px; }
  .top { align-items: stretch; flex-direction: column; padding: 24px 20px; }
  .top :deep(.el-button) { width: 100%; }
  .desktop-table { display: none; }
  .mobile-data-list { display: grid; gap: 12px; padding: 6px 14px 16px; list-style: none; }
  .mobile-data-card { display: grid; gap: 14px; padding: 16px; border: 1px solid $color-border; border-radius: $radius-md; background: $color-surface; }
  .mobile-data-card header { display: flex; align-items: baseline; justify-content: space-between; gap: 12px; }
  .mobile-data-card header strong { min-width: 0; overflow-wrap: anywhere; font-size: 16px; }
  .mobile-data-card header span { flex: 0 0 auto; color: $color-text-secondary; font-family: $font-numeric; font-size: 12px; }
  .mobile-data-card dl { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; margin: 0; }
  .mobile-data-card dl div { min-width: 0; }
  .mobile-data-card dt { color: $color-text-secondary; font-size: 12px; }
  .mobile-data-card dd { margin: 3px 0 0; overflow-wrap: anywhere; color: $color-text-primary; font-size: 13px; font-weight: 700; }
  .mobile-card-actions { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }
  .mobile-card-actions :deep(.el-button) { width: 100%; min-height: 44px; margin: 0; }
  .mobile-empty { padding: 32px 16px; color: $color-text-secondary; text-align: center; }
  .form-grid,
  .nutrition-grid { grid-template-columns: 1fr; }
  :global(.ingredient-editor-dialog .el-dialog__body) { padding-inline: 16px; }
}

@media (max-width: 420px) {
  .mobile-data-card dl { grid-template-columns: 1fr; }
}

@media (prefers-reduced-motion: reduce) {
  :global(.ingredient-editor-dialog),
  :global(.ingredient-editor-dialog *) { scroll-behavior: auto; }
}
</style>
