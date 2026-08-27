<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { AdminIngredient, AdminIngredientInput } from '@/api/admin'
import { createIngredient, deleteIngredient, listIngredients, updateIngredient } from '@/api/admin'

const items = ref<AdminIngredient[]>([])
const loading = ref(false)
const dialogVisible = ref(false)
const editingId = ref<number | null>(null)
const emptyForm = (): AdminIngredientInput => ({ name: '', category: 'vegetable', unit: 'g', unit_price: 0, season_tags: null, storage_days: 7, nutrition: { calories: 0, protein: 0, fat: 0, carbs: 0, fiber: 0 } })
const form = reactive<AdminIngredientInput>(emptyForm())

async function load() { loading.value = true; try { items.value = await listIngredients() } catch (e: any) { ElMessage.error(e.message || '加载失败') } finally { loading.value = false } }
function openCreate() { editingId.value = null; Object.assign(form, emptyForm()); dialogVisible.value = true }
function openEdit(item: AdminIngredient) { editingId.value = item.ingredient_id; Object.assign(form, JSON.parse(JSON.stringify({ ...item, ingredient_id: undefined }))); dialogVisible.value = true }
async function save() { if (!form.name.trim()) return ElMessage.warning('请填写食材名称'); try { if (editingId.value) await updateIngredient(editingId.value, form); else await createIngredient(form); ElMessage.success('已保存'); dialogVisible.value = false; await load() } catch (e: any) { ElMessage.error(e.message || '保存失败') } }
async function remove(item: AdminIngredient) { try { await ElMessageBox.confirm(`确定删除「${item.name}」吗？`, '确认删除', { type: 'warning' }); await deleteIngredient(item.ingredient_id); ElMessage.success('已删除'); await load() } catch (e: any) { if (e !== 'cancel' && e !== 'close') ElMessage.error(e.message || '删除失败') } }
onMounted(load)
</script>

<template>
  <div class="page-container admin-ingredients">
    <div class="top"><div><h1>食材库维护</h1><p>价格和营养数据会直接影响预算与方案计算。</p></div><el-button type="primary" @click="openCreate">新增食材</el-button></div>
    <el-table v-loading="loading" :data="items" class="card"><el-table-column prop="name" label="食材" min-width="120" /><el-table-column prop="category" label="分类" width="110" /><el-table-column label="采购价格" width="150"><template #default="{ row }">¥{{ row.unit_price }}/{{ row.unit }}</template></el-table-column><el-table-column label="热量 / 100g" width="140"><template #default="{ row }">{{ row.nutrition.calories }} kcal</template></el-table-column><el-table-column label="操作" width="150"><template #default="{ row }"><el-button link type="primary" @click="openEdit(row)">编辑</el-button><el-button link type="danger" @click="remove(row)">删除</el-button></template></el-table-column></el-table>
    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑食材' : '新增食材'" width="560px"><el-form label-width="105px"><el-form-item label="食材名称"><el-input v-model="form.name" /></el-form-item><el-form-item label="分类"><el-select v-model="form.category"><el-option v-for="item in ['vegetable','meat','seafood','dairy','grain','fruit','condiment','egg','other']" :key="item" :value="item" /></el-select></el-form-item><el-form-item label="采购单位 / 价格"><el-input v-model="form.unit" style="width:100px" /><el-input-number v-model="form.unit_price" :min="0" :precision="2" style="margin-left:12px" /></el-form-item><el-form-item label="建议存放天数"><el-input-number v-model="form.storage_days" :min="0" /></el-form-item><el-divider>每 100g 营养</el-divider><el-row :gutter="12"><el-col :span="12"><el-form-item label="热量 kcal"><el-input-number v-model="form.nutrition.calories" :min="0" /></el-form-item></el-col><el-col :span="12"><el-form-item label="蛋白质 g"><el-input-number v-model="form.nutrition.protein" :min="0" /></el-form-item></el-col><el-col :span="12"><el-form-item label="脂肪 g"><el-input-number v-model="form.nutrition.fat" :min="0" /></el-form-item></el-col><el-col :span="12"><el-form-item label="碳水 g"><el-input-number v-model="form.nutrition.carbs" :min="0" /></el-form-item></el-col></el-row></el-form><template #footer><el-button @click="dialogVisible=false">取消</el-button><el-button type="primary" @click="save">保存</el-button></template></el-dialog>
  </div>
</template>

<style scoped lang="scss">
.admin-ingredients { max-width: 1200px; padding-top: 44px; padding-bottom: 88px; }
.top { display: flex; align-items: center; justify-content: space-between; gap: 24px; margin-bottom: 22px; padding: 28px 30px; border: 1px solid rgba($color-sage-dark,.1); border-radius: $radius-xl; background: linear-gradient(135deg, $color-surface-soft, rgba($color-lime-soft,.7)); }
.top h1 { margin: 0 0 6px; font-size: clamp(28px,4vw,40px); letter-spacing: -.04em; }.top p { margin: 0; color: $color-text-secondary; }
.el-table { width: 100%; padding: 12px; overflow: hidden; border-radius: $radius-lg; box-shadow: $shadow-sm; }
:deep(.el-table th.el-table__cell) { height: 52px; background: $color-surface-soft; color: $color-text-secondary; font-size: 12px; }
:deep(.el-table td.el-table__cell) { height: 56px; }
:global(.el-dialog) { max-width: calc(100vw - 32px); border-radius: $radius-lg; }
@media (max-width: $breakpoint-sm) {
  .admin-ingredients { padding-top: 24px; }
  .top { align-items: stretch; flex-direction: column; padding: 24px 20px; }
  .top :deep(.el-button) { width: 100%; }
  .el-table { overflow-x: auto; }
  .el-table :deep(.el-table__inner-wrapper) { min-width: 720px; }
  :global(.el-dialog__body) { padding-inline: 16px; }
  :global(.el-dialog .el-form-item) { display: block; }
  :global(.el-dialog .el-form-item__label) { width: auto !important; }
  :global(.el-dialog .el-form-item__content) { margin-left: 0 !important; }
  :global(.el-dialog .el-col-12) { max-width: 100%; flex: 0 0 100%; }
}
</style>
