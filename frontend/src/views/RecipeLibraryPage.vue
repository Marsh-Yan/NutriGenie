<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import EmptyState from '@/components/common/EmptyState.vue'
import ErrorState from '@/components/common/ErrorState.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import PageSkeleton from '@/components/common/PageSkeleton.vue'
import { getRecipes } from '@/api/recipes'
import type { RecipeListItem } from '@/types'

const route = useRoute()
const router = useRouter()
const recipes = ref<RecipeListItem[]>([])
const total = ref(0)
const loading = ref(false)
const error = ref('')
let requestSequence = 0

const filters = reactive({ category: '', cuisine_type: '', difficulty: '', max_prep_time: '' })
const categoryOptions = [
  { value: 'main_dish', label: '主菜' },
  { value: 'side_dish', label: '配菜' },
  { value: 'staple', label: '主食' },
  { value: 'light_meal', label: '轻食' },
  { value: 'soup', label: '汤羹' },
]
const categoryLabels = Object.fromEntries(categoryOptions.map(item => [item.value, item.label]))
const cuisineLabels: Record<string, string> = { chinese: '中式', western: '西式' }
const difficultyLabels: Record<string, string> = { easy: '简单', medium: '适中', hard: '进阶' }

function queryValue(value: unknown) {
  return typeof value === 'string' ? value : ''
}

function syncFilters() {
  filters.category = queryValue(route.query.category)
  filters.cuisine_type = queryValue(route.query.cuisine_type)
  filters.difficulty = queryValue(route.query.difficulty)
  filters.max_prep_time = queryValue(route.query.max_prep_time)
}

async function loadRecipes() {
  const sequence = ++requestSequence
  loading.value = true
  error.value = ''
  try {
    const response = await getRecipes({
      category: queryValue(route.query.category) || undefined,
      cuisine_type: queryValue(route.query.cuisine_type) || undefined,
      difficulty: queryValue(route.query.difficulty) || undefined,
      max_prep_time: Number(queryValue(route.query.max_prep_time)) || undefined,
      page: Math.max(1, Number(queryValue(route.query.page)) || 1),
      page_size: 12,
    })
    if (sequence !== requestSequence) return
    recipes.value = response.items
    total.value = response.total
  } catch (cause: unknown) {
    if (sequence !== requestSequence) return
    recipes.value = []
    total.value = 0
    error.value = cause instanceof Error ? cause.message : '菜谱列表加载失败'
  } finally {
    if (sequence === requestSequence) loading.value = false
  }
}

watch(
  () => [route.query.category, route.query.cuisine_type, route.query.difficulty, route.query.max_prep_time, route.query.page],
  () => {
    syncFilters()
    loadRecipes()
  },
  { immediate: true },
)

function applyFilters() {
  router.replace({
    name: 'recipe-library',
    query: {
      category: filters.category || undefined,
      cuisine_type: filters.cuisine_type || undefined,
      difficulty: filters.difficulty || undefined,
      max_prep_time: filters.max_prep_time || undefined,
      page: undefined,
    },
  })
}

function resetFilters() {
  Object.assign(filters, { category: '', cuisine_type: '', difficulty: '', max_prep_time: '' })
  router.replace({ name: 'recipe-library' })
}

function changePage(page: number) {
  router.replace({ query: { ...route.query, page: page > 1 ? String(page) : undefined } })
}
</script>

<template>
  <div class="recipe-library page-container">
    <PageHeader
      kicker="标准菜谱库"
      title="先看清做法，再决定今天吃什么。"
      description="菜谱、用量、营养和成本来自当前后端菜谱库。筛选条件会保留在 URL 中，方便返回和分享。"
    />

    <form class="filter-panel card" aria-label="菜谱筛选" @submit.prevent="applyFilters">
      <label>
        <span>菜谱类型</span>
        <el-select v-model="filters.category" placeholder="不限类型" clearable>
          <el-option v-for="item in categoryOptions" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
      </label>
      <label>
        <span>菜系</span>
        <el-select v-model="filters.cuisine_type" placeholder="不限菜系" clearable>
          <el-option label="中式" value="chinese" />
          <el-option label="西式" value="western" />
        </el-select>
      </label>
      <label>
        <span>难度</span>
        <el-select v-model="filters.difficulty" placeholder="不限难度" clearable>
          <el-option label="简单" value="easy" />
          <el-option label="适中" value="medium" />
          <el-option label="进阶" value="hard" />
        </el-select>
      </label>
      <label>
        <span>准备时间</span>
        <el-select v-model="filters.max_prep_time" placeholder="不限时间" clearable>
          <el-option label="15 分钟内" value="15" />
          <el-option label="30 分钟内" value="30" />
          <el-option label="45 分钟内" value="45" />
        </el-select>
      </label>
      <div class="filter-actions">
        <el-button native-type="button" @click="resetFilters">重置</el-button>
        <el-button type="primary" native-type="submit" :loading="loading">应用筛选</el-button>
      </div>
    </form>

    <PageSkeleton v-if="loading" :rows="4" class="library-state" />
    <ErrorState v-else-if="error" class="library-state" :message="error" retry-label="重新加载" @retry="loadRecipes" />
    <EmptyState
      v-else-if="!recipes.length"
      class="library-state"
      title="没有符合条件的菜谱"
      description="可以减少一个筛选条件，或清空筛选后查看完整菜谱库。"
    >
      <template #actions><el-button type="primary" @click="resetFilters">清空筛选</el-button></template>
    </EmptyState>

    <template v-else>
      <div class="result-heading" aria-live="polite"><strong>{{ total }}</strong><span>道符合条件的菜谱</span></div>
      <section class="recipe-grid" aria-label="菜谱列表">
        <article v-for="recipe in recipes" :key="recipe.recipe_id" class="recipe-item card">
          <div class="recipe-mark" aria-hidden="true">{{ recipe.name.slice(0, 1) }}</div>
          <div class="recipe-copy">
            <div class="recipe-labels">
              <span>{{ categoryLabels[recipe.category] || recipe.category }}</span>
              <span>{{ cuisineLabels[recipe.cuisine_type] || recipe.cuisine_type }}</span>
              <span>{{ difficultyLabels[recipe.difficulty] || recipe.difficulty }}</span>
            </div>
            <h2>{{ recipe.name }}</h2>
            <p>{{ recipe.total_calories.toFixed(0) }} kcal · 准备 {{ recipe.prep_time }} 分钟 · 烹饪 {{ recipe.cook_time }} 分钟</p>
            <div v-if="recipe.tags?.length" class="recipe-tags" aria-label="菜谱标签">
              <span v-for="tag in recipe.tags.slice(0, 3)" :key="tag">{{ tag }}</span>
            </div>
          </div>
          <router-link :to="{ name: 'recipe-detail', params: { id: recipe.recipe_id } }" class="detail-link">查看做法</router-link>
        </article>
      </section>

      <el-pagination
        v-if="total > 12"
        class="pagination"
        layout="prev, pager, next"
        :page-size="12"
        :current-page="Math.max(1, Number(queryValue(route.query.page)) || 1)"
        :total="total"
        @current-change="changePage"
      />
    </template>
  </div>
</template>

<style scoped lang="scss">
.recipe-library { padding-bottom: 96px; }
.filter-panel { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)) auto; align-items: end; gap: 12px; margin-top: 24px; padding: 18px; }
.filter-panel label { display: grid; gap: 7px; min-width: 0; }
.filter-panel label > span { color: $color-text-secondary; font-size: 13px; font-weight: 720; }
.filter-panel :deep(.el-select) { width: 100%; }
.filter-panel :deep(.el-select__wrapper) { min-height: 44px; }
.filter-actions { display: flex; gap: 8px; }
.filter-actions .el-button { min-height: 44px; margin: 0; }
.library-state { margin-top: 28px; }
.result-heading { display: flex; align-items: baseline; gap: 7px; margin: 28px 0 14px; color: $color-text-secondary; font-size: 14px; }
.result-heading strong { color: $color-sage-dark; font-size: 24px; }
.recipe-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; }
.recipe-item { display: grid; grid-template-columns: 70px minmax(0, 1fr) auto; align-items: center; gap: 16px; min-height: 156px; padding: 20px; }
.recipe-mark { display: grid; width: 70px; height: 92px; place-items: center; border-radius: $radius-md; background: linear-gradient(145deg, $color-lime-soft, $color-surface-warm); color: $color-sage-dark; font-size: 28px; font-weight: 820; }
.recipe-copy { min-width: 0; }
.recipe-labels, .recipe-tags { display: flex; flex-wrap: wrap; gap: 6px; }
.recipe-labels span, .recipe-tags span { padding: 3px 7px; border-radius: $radius-round; background: $color-surface-soft; color: $color-text-secondary; font-size: 12px; font-weight: 680; }
.recipe-copy h2 { margin-top: 9px; font-size: 19px; letter-spacing: -.02em; }
.recipe-copy p { margin-top: 6px; color: $color-text-secondary; font-size: 13px; line-height: 1.55; }
.recipe-tags { margin-top: 9px; }
.recipe-tags span { background: $color-lime-soft; color: $color-sage-dark; }
.detail-link { display: inline-flex; min-height: 44px; align-items: center; padding: 8px 12px; border: 1px solid rgba($color-sage, .24); border-radius: $radius-sm; color: $color-sage-dark; font-size: 13px; font-weight: 760; white-space: nowrap; }
.detail-link:hover { border-color: $color-sage; background: $color-lime-soft; color: $color-sage-dark; }
.pagination { justify-content: center; margin-top: 28px; }

@media (max-width: $breakpoint-lg) {
  .filter-panel { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .filter-actions { grid-column: 1 / -1; justify-content: flex-end; }
  .recipe-grid { grid-template-columns: 1fr; }
}

@media (max-width: $breakpoint-sm) {
  .recipe-library { padding-bottom: 64px; }
  .filter-panel { grid-template-columns: 1fr; padding: 15px; }
  .filter-actions { grid-column: auto; display: grid; grid-template-columns: 1fr 1fr; }
  .recipe-item { grid-template-columns: 58px minmax(0, 1fr); gap: 13px; padding: 16px; }
  .recipe-mark { width: 58px; height: 76px; }
  .detail-link { grid-column: 1 / -1; justify-content: center; }
}
</style>
