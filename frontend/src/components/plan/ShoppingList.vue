<script setup lang="ts">
import { ref } from 'vue'
import type { ShoppingList as ShoppingListType } from '@/types'
import { ArrowDown } from '@element-plus/icons-vue'
import PremiumIcon from '@/components/common/PremiumIcon.vue'

const props = defineProps<{
  shoppingList: ShoppingListType
}>()

const expandedCats = ref<Set<string>>(new Set(Object.keys(props.shoppingList.by_category || {})))
const checkedItems = ref<Set<string>>(new Set())
const copyFeedback = ref('复制清单')

function toggleCat(cat: string) {
  if (expandedCats.value.has(cat)) {
    expandedCats.value.delete(cat)
  } else {
    expandedCats.value.add(cat)
  }
}

function toggleItem(key: string) {
  const next = new Set(checkedItems.value)
  next.has(key) ? next.delete(key) : next.add(key)
  checkedItems.value = next
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
    <h3 class="section-title">
      <span class="title-main"><PremiumIcon name="shopping" class="section-icon" :size="16" :box-size="32" />采购清单</span>
      <span class="title-actions"><button type="button" class="copy-button" @click="copyList">{{ copyFeedback }}</button><span class="total-cost">预计 ¥{{ shoppingList.total_cost.toFixed(1) }}</span></span>
    </h3>

    <div v-if="Object.keys(shoppingList.by_category || {}).length === 0" class="empty-state">
      暂无采购清单数据
    </div>

    <div v-for="(items, cat) in shoppingList.by_category" :key="cat" class="category-group">
      <button class="category-header" type="button" :aria-expanded="expandedCats.has(cat)" @click="toggleCat(cat)">
        <span class="category-name">{{ cat }}</span>
        <span class="category-count">{{ items.length }} 项</span>
        <el-icon class="cat-arrow" :class="{ rotated: expandedCats.has(cat) }">
          <ArrowDown />
        </el-icon>
      </button>

      <transition name="collapse">
        <div v-if="expandedCats.has(cat)" class="category-items">
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
  margin-bottom: 32px;
}

.section-title {
  font-size: 18px;
  font-weight: 600;
  color: $color-text-primary;
  margin-bottom: 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.title-main {
  display: inline-flex;
  align-items: center;
  gap: 9px;
}

.section-icon {
  border-radius: 10px;
  box-shadow: none;
}

.total-cost {
  font-size: 14px;
  font-weight: 700;
  color: $color-rose-dark;
}
.title-actions { display: inline-flex; align-items: center; gap: 10px; }
.copy-button { padding: 5px 9px; border: 1px solid $color-border; border-radius: 999px; background: $color-card; color: $color-sage-dark; cursor: pointer; font: inherit; font-size: 12px; }

.empty-state {
  text-align: center;
  padding: 24px;
  color: $color-text-placeholder;
  font-size: 14px;
}

// 分类组

.category-group {
  background: $color-card;
  border: 1px solid $color-border;
  border-radius: $radius-md;
  overflow: hidden;
  margin-bottom: 8px;
}

.category-header {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 12px 16px;
  border: none;
  background: transparent;
  cursor: pointer;
  font-size: 14px;
  color: $color-text-primary;
  transition: background 0.2s;

  &:hover {
    background: rgba($color-sage, 0.03);
  }
}

.category-name {
  font-weight: 600;
}

.category-count {
  font-size: 12px;
  color: $color-text-secondary;
  margin-left: auto;
}

.cat-arrow {
  font-size: 14px;
  color: $color-text-placeholder;
  transition: transform 0.2s;

  &.rotated {
    transform: rotate(180deg);
  }
}

// 物品列表

.collapse-enter-active, .collapse-leave-active {
  transition: all 0.2s ease;
}

.collapse-enter-from, .collapse-leave-to {
  opacity: 0;
  max-height: 0;
}

.category-items {
  border-top: 1px solid $color-divider;
}

.item-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 16px;

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
}
.item-row.checked { opacity: .58; }
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
</style>
