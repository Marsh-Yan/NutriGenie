<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getKnowledgeDocument, listKnowledgeDocuments, rebuildKnowledgeIndex, saveKnowledgeDocument, uploadKnowledgeDocument, type KnowledgeDocument } from '@/api/admin'

const documents = ref<KnowledgeDocument[]>([])
const activeId = ref<number | null>(null)
const content = ref('')
const loading = ref(false); const saving = ref(false); const rebuilding = ref(false); const uploading = ref(false)
const uploadInput = ref<HTMLInputElement | null>(null)
async function loadList() { loading.value = true; try { documents.value = await listKnowledgeDocuments() } catch (e:any) { ElMessage.error(e.message || '加载失败') } finally { loading.value = false } }
async function select(id:number) { try { activeId.value = id; content.value = (await getKnowledgeDocument(id)).content } catch (e:any) { ElMessage.error(e.message || '读取文档失败') } }
async function save() { if (!activeId.value) return; saving.value = true; try { await saveKnowledgeDocument(activeId.value, content.value); ElMessage.success('文档已保存，请按需重建索引'); await loadList() } catch (e:any) { ElMessage.error(e.message || '保存失败') } finally { saving.value = false } }
async function upload(event: Event) { const file = (event.target as HTMLInputElement).files?.[0]; if (!file) return; uploading.value = true; try { const result = await uploadKnowledgeDocument(file); ElMessage.success(`已导入 ${result.source_file}，请按需重建索引`); await loadList(); await select(result.recipe_id) } catch (e:any) { ElMessage.error(e.message || '上传失败') } finally { uploading.value = false; if (uploadInput.value) uploadInput.value.value = '' } }
async function rebuild() { try { await ElMessageBox.confirm('重建会调用远程 Embedding API 并覆盖当前向量索引，是否继续？', '确认重建知识库', { type:'warning' }); rebuilding.value = true; const result = await rebuildKnowledgeIndex(); ElMessage.success(`索引重建完成，共 ${result.indexed_documents} 篇文档`) } catch (e:any) { if (e !== 'cancel' && e !== 'close') ElMessage.error(e.message || '重建失败') } finally { rebuilding.value = false } }
onMounted(loadList)
</script>

<template>
  <div class="page-container knowledge-admin">
    <div class="top"><div><h1>知识库维护</h1><p>上传 UTF-8 的 Markdown 文件，或直接维护已收录文档。</p></div><div class="tools"><input ref="uploadInput" type="file" accept=".md,text/markdown,text/plain" hidden @change="upload" /><el-button :loading="uploading" @click="uploadInput?.click()">上传 Markdown</el-button><el-button type="primary" :loading="rebuilding" @click="rebuild">重建向量索引</el-button></div></div>
    <el-alert type="info" :closable="false" title="上传文件必须包含 frontmatter 与已有菜谱的 recipe_id；上传和保存不会自动调用 Embedding。" />
    <div class="workspace card" v-loading="loading"><aside><div class="aside-title">已收录文档</div><button v-for="doc in documents" :key="doc.recipe_id" :class="{ active: activeId === doc.recipe_id }" @click="select(doc.recipe_id)">菜谱 #{{ doc.recipe_id }}<small>{{ doc.source_file }}</small></button></aside><section><el-empty v-if="!activeId" description="从左侧选择文档，或上传新的 Markdown 文件" /><template v-else><p class="hint">保留 frontmatter 中匹配的 <code>recipe_id</code>，保存后再手动重建索引。</p><el-input v-model="content" type="textarea" :rows="25" class="markdown-editor" /><div class="save-row"><el-button type="primary" :loading="saving" @click="save">保存 Markdown</el-button></div></template></section></div>
  </div>
</template>

<style scoped lang="scss">
.knowledge-admin{max-width:1180px;padding-top:44px}.top{display:flex;justify-content:space-between;align-items:center;margin-bottom:18px}h1{margin:0 0 6px}.top p{margin:0;color:$color-text-secondary}.tools{display:flex;gap:10px}.el-alert{margin-bottom:16px}.workspace{display:grid;grid-template-columns:230px 1fr;min-height:600px;overflow:hidden;padding:0}aside{border-right:1px solid $color-border;padding:16px;display:grid;align-content:start;gap:6px}.aside-title{font-size:13px;color:$color-text-secondary;margin-bottom:6px}aside button{text-align:left;background:transparent;border:0;border-radius:$radius-sm;padding:10px;cursor:pointer;color:$color-text-primary}aside button.active,aside button:hover{background:rgba($color-sage,0.12)}small{display:block;color:$color-text-secondary;margin-top:3px}section{padding:20px}.hint{font-size:13px;color:$color-text-secondary;margin:0 0 12px}.markdown-editor :deep(textarea){font-family:ui-monospace,SFMono-Regular,Consolas,monospace;line-height:1.55}.save-row{margin-top:14px;text-align:right}@media(max-width:$breakpoint-sm){.workspace{grid-template-columns:1fr}aside{border-right:0;border-bottom:1px solid $color-border}.top{align-items:flex-start;gap:12px}.tools{flex-wrap:wrap}}
</style>
