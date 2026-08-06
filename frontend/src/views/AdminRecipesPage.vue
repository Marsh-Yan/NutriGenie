<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { deleteRecipe, getRecipeDetail, listRecipes, updateRecipe } from '@/api/admin'

const recipes = ref<any[]>([])
const loading = ref(false)
const editorVisible = ref(false)
const editorValue = ref('')
const activeId = ref<number | null>(null)

async function load() { loading.value = true; try { recipes.value = (await listRecipes()).items } catch (e:any) { ElMessage.error(e.message || '加载失败') } finally { loading.value = false } }
async function edit(row: any) { try { const detail = await getRecipeDetail(row.recipe_id); activeId.value = row.recipe_id; editorValue.value = JSON.stringify({ name: detail.name, description: detail.description, category: detail.category, cuisine_type: detail.cuisine_type, difficulty: detail.difficulty, prep_time: detail.prep_time, cook_time: detail.cook_time, servings: detail.servings, steps: detail.steps, image_url: detail.image_url, nutrition: detail.nutrition || { calories: 0, protein: 0, fat: 0, carbs: 0, fiber: 0 }, tags: detail.tags, ingredients: detail.ingredients.map((item:any) => ({ ingredient_id: item.ingredient_id, quantity: item.quantity, unit: item.unit, is_optional: item.is_optional })) }, null, 2); editorVisible.value = true } catch (e:any) { ElMessage.error(e.message || '加载菜谱失败') } }
async function save() { if (!activeId.value) return; try { await updateRecipe(activeId.value, JSON.parse(editorValue.value)); ElMessage.success('菜谱已保存'); editorVisible.value = false; await load() } catch (e:any) { ElMessage.error(e.message || '保存失败：请检查 JSON 格式与食材编号') } }
async function remove(row:any) { try { await ElMessageBox.confirm(`确定删除「${row.name}」吗？`, '确认删除', { type: 'warning' }); await deleteRecipe(row.recipe_id); ElMessage.success('已删除'); await load() } catch (e:any) { if (e !== 'cancel' && e !== 'close') ElMessage.error(e.message || '删除失败') } }
onMounted(load)
</script>

<template>
  <div class="page-container recipe-admin">
    <div class="top"><div><h1>菜谱库维护</h1><p>菜谱变更后请在知识库页面同步更新对应 Markdown。</p></div></div>
    <el-alert type="info" :closable="false" title="当前编辑器保留完整菜谱结构，适合维护已有菜谱；用料请填写已有食材的 ingredient_id。" />
    <el-table v-loading="loading" :data="recipes" class="card"><el-table-column prop="name" label="菜谱" min-width="180" /><el-table-column prop="category" label="分类" width="110" /><el-table-column prop="difficulty" label="难度" width="100" /><el-table-column label="耗时" width="110"><template #default="{row}">{{ row.prep_time + row.cook_time }} 分钟</template></el-table-column><el-table-column label="操作" width="150"><template #default="{row}"><el-button link type="primary" @click="edit(row)">编辑</el-button><el-button link type="danger" @click="remove(row)">删除</el-button></template></el-table-column></el-table>
    <el-dialog v-model="editorVisible" title="编辑菜谱数据" width="760px"><p class="hint">保存前请确认 nutrition、steps 与 ingredients 均完整；食材编号可在“食材库维护”中查看。</p><el-input v-model="editorValue" type="textarea" :rows="22" class="json-editor" /><template #footer><el-button @click="editorVisible=false">取消</el-button><el-button type="primary" @click="save">保存菜谱</el-button></template></el-dialog>
  </div>
</template>

<style scoped lang="scss">
.recipe-admin{max-width:1080px;padding-top:44px}.top{margin-bottom:22px;h1{margin:0 0 6px}p{margin:0;color:$color-text-secondary}}.el-alert{margin-bottom:16px}.el-table{padding:10px;border-radius:$radius-lg;overflow:hidden}.hint{font-size:13px;color:$color-text-secondary;margin:0 0 12px}.json-editor :deep(textarea){font-family:ui-monospace,SFMono-Regular,Consolas,monospace;font-size:12px;line-height:1.55}
</style>
