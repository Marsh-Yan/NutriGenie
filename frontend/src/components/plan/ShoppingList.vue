<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { ShoppingList as ShoppingListType } from '@/types'
import { ArrowDown } from '@element-plus/icons-vue'
import PremiumIcon from '@/components/common/PremiumIcon.vue'

const props = defineProps<{
  shoppingList: ShoppingListType
  checkedKeys?: string[]
}>()

const emit = defineEmits<{
  toggle: [key: string]
  reset: []
}>()

const expandedCats = ref<Set<string>>(new Set(Object.keys(props.shoppingList.by_category || {})))
const copyFeedback = ref('复制清单')
const checkedItems = computed(() => new Set(props.checkedKeys || []))
const totalItems = computed(() => Object.values(props.shoppingList.by_category || {}).reduce((total, items) => total + items.length, 0))
const checkedCount = computed(() => Math.min(checkedItems.value.size, totalItems.value))

watch(() => props.shoppingList, (shoppingList) => {
  expandedCats.value = new Set(Object.keys(shoppingList.by_category || {}))
  copyFeedback.value = '复制清单'
})

function toggleCat(cat: string) {
  if (expandedCats.value.has(cat)) {
    expandedCats.value.delete(cat)
  } else {
    expandedCats.value.add(cat)
  }
}

function toggleItem(key: string) {
  emit('toggle', key)
}

function printList() {
  window.print()
}

async function copyList() {
  const lines = Object.entries(props.shoppingList.by_category || {}).flatMap(([cat, items]) => [
    `【${cat}】`,
    ...items.map(item => `- ${item.name} ${item.quantity}${item.unit}（约 ¥${item.estimated_cost.toFixed(1)}）`),
  ])
  try {
    await navigator.clipboard.writeText(`NutriGenie 采购清单\n${lines.join('\n')}\n预计 ¥${props.shoppingList.total_cost.toFixed(1)}`)
    copyFeedback.value = '已复制'
    window.setTimeout(() => { copyFeedback.value = '复制清单' }, 1600)
  } catch {
    copyFeedback.value = '复制失败'
  }
}
</script>

<template>
  <div class="shopping-list">
    <div class="section-heading">
      <h3 class="section-title"><PremiumIcon name="shopping" class="section-icon" :size="16" :box-size="32" />采购清单</h3>
      <div class="title-actions">
        <span class="shopping-progress">已备 {{ checkedCount }}/{{ totalItems }}</span>
        <button v-if="checkedCount" type="button" class="copy-button" @click="emit('reset')">全部重置</button>
        <button type="button" class="copy-button" @click="copyList">
          <span aria-live="polite">{{ copyFeedback }}</span>
        </button>
        <button type="button" class="copy-button" @click="printList">打印</button>
        <span class="total-cost"><small>预计</small> ¥{{ shoppingList.total_cost.toFixed(1) }}</span>
      </div>
    </div>

    <div v-if="Object.keys(shoppingList.by_category || {}).length === 0" class="empty-state">
      暂无采购清单数据
    </div>

    <div v-for="(items, cat, catIndex) in shoppingList.by_category" :key="cat" class="category-group">
      <button
        class="category-header"
        type="button"
        :aria-expanded="expandedCats.has(cat)"
        :aria-controls="`shopping-category-${catIndex}`"
        @click="toggleCat(cat)"
      >
        <span class="category-name">{{ cat }}</span>
        <span class="category-count">{{ items.length }} 项</span>
        <el-icon class="cat-arrow" :class="{ rotated: expandedCats.has(cat) }">
          <ArrowDown />
        </el-icon>
      </button>

      <transition name="collapse">
        <div v-if="expandedCats.has(cat)" :id="`shopping-category-${catIndex}`" class="category-items">
          <div v-for="item in items" :key="item.name" class="item-row" :class="{ checked: checkedItems.has(`${cat}-${item.name}`) }">
            <label class="item-name"><input type="checkbox" :checked="checkedItems.has(`${cat}-${item.name}`)" @change="toggleItem(`${cat}-${item.name}`)" />{{ item.name }}</label>
            <span class="item-quantity">{{ item.quantity }} {{ item.unit }}</span>
            <span class="item-cost">¥{{ item.estimated_cost.toFixed(1) }}</span>
          </div>
        </div>
      </transition>
    </div>
  </div>
</template>

<style scoped lang="scss">
.shopping-list {
  width: 100%;
}

.section-heading {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  margin-bottom: 18px;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 9px;
  margin: 0;
  color: $color-text-primary;
  font-size: 19px;
  font-weight: 750;
}

.section-icon {
  border-radius: 10px;
  box-shadow: none;
}

.total-cost {
  display: inline-flex;
  align-items: baseline;
  gap: 4px;
  padding: 6px 10px;
  border-radius: 999px;
  background: $color-surface-warm;
  color: $color-rose-dark;
  font-size: 14px;
  font-variant-numeric: tabular-nums;
  font-weight: 800;

  small { color: $color-text-secondary; font-size: 12px; font-weight: 650; }
}
.title-actions { display: inline-flex; align-items: center; gap: 10px; }
.shopping-progress { color: $color-text-secondary; font-size: 13px; font-weight: 700; }
.copy-button {
  min-height: 32px;
  padding: 5px 11px;
  border: 1px solid rgba($color-sage, .22);
  border-radius: 999px;
  background: $color-card;
  color: $color-sage-dark;
  box-shadow: $shadow-xs;
  cursor: pointer;
  font: inherit;
  font-size: 12px;
  font-weight: 700;
  transition: border-color .2s ease, background-color .2s ease, transform .2s ease;

  &:hover { border-color: rgba($color-sage, .5); background: $color-surface-soft; transform: translateY(-1px); }
}

.empty-state {
  padding: 28px 20px;
  border: 1px dashed rgba($color-sage, .28);
  border-radius: $radius-md;
  background: $color-surface-soft;
  color: $color-text-placeholder;
  font-size: 14px;
  text-align: center;
}

// 分类组

.category-group {
  border: 1px solid rgba($color-sage-dark, .11);
  border-radius: $radius-md;
  background: rgba($color-card, .9);
  box-shadow: $shadow-xs;
  overflow: hidden;
  margin-bottom: 10px;
  transition: border-color .2s ease, box-shadow .2s ease;

  &:has(.category-header[aria-expanded='true']) {
    border-color: rgba($color-sage, .24);
    box-shadow: $shadow-sm;
  }
}

.category-header {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  min-height: 50px;
  padding: 12px 14px 12px 16px;
  border: none;
  background: transparent;
  cursor: pointer;
  font-size: 14px;
  color: $color-text-primary;
  transition: background 0.2s;

  &:hover {
    background: rgba($color-sage, .045);
  }
}

.category-name {
  font-weight: 750;
}

.category-count {
  font-size: 12px;
  color: $color-text-secondary;
  margin-left: auto;
}

.cat-arrow {
  display: grid;
  place-items: center;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: $color-surface-soft;
  font-size: 14px;
  color: $color-text-placeholder;
  transition: transform 0.2s;

  &.rotated {
    transform: rotate(180deg);
  }
}

// 物品列表

.collapse-enter-active, .collapse-leave-active {
  transition: max-height 0.2s ease, opacity 0.2s ease;
}

.collapse-enter-from, .collapse-leave-to {
  opacity: 0;
  max-height: 0;
}

.category-items {
  border-top: 1px solid $color-divider;
  background: linear-gradient(180deg, rgba($color-surface-soft, .44), rgba($color-card, .88));
}

.item-row {
  display: flex;
  align-items: center;
  gap: 12px;
  min-height: 46px;
  padding: 10px 16px;
  transition: background-color .2s ease, opacity .2s ease;

  & + & {
    border-top: 1px solid $color-divider;
  }
}

.item-name {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: $color-text-primary;

  input {
    width: 17px;
    height: 17px;
    flex: 0 0 auto;
    accent-color: $color-sage-dark;
    cursor: pointer;
  }
}
.item-row.checked { background: rgba($color-sage, .045); opacity: .62; }
.item-row.checked .item-name { text-decoration: line-through; }

.item-quantity {
  font-size: 13px;
  color: $color-text-secondary;
}

.item-cost {
  font-size: 14px;
  font-weight: 600;
  color: $color-text-primary;
  min-width: 50px;
  text-align: right;
}

@media (max-width: $breakpoint-sm) {
  .section-heading { align-items: flex-start; flex-direction: column; gap: 10px; }
  .title-actions { width: 100%; justify-content: space-between; }

  .item-row {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 5px 12px;
    padding-block: 12px;
  }

  .item-name { grid-column: 1 / -1; }
  .item-quantity { padding-left: 25px; }
  .item-cost { min-width: auto; }
}

@media print {
  .copy-button { display: none; }
  .shopping-list { color: #111; }
}
</style>
