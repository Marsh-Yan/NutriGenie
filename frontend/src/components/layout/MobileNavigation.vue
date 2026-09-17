<script setup lang="ts">
import { useRoute } from 'vue-router'
import PremiumIcon from '@/components/common/PremiumIcon.vue'
import type { PremiumIconName } from '@/components/common/PremiumIcon.vue'

const route = useRoute()

type NavigationItem = {
  to: string
  label: string
  icon: PremiumIconName
  routeNames: string[]
}

const items: NavigationItem[] = [
  { to: '/dashboard', label: '今日', icon: 'home', routeNames: ['dashboard'] },
  { to: '/plans', label: '计划', icon: 'clipboard', routeNames: ['plan-history', 'plan-result'] },
  { to: '/plan/new', label: '创建', icon: 'plan', routeNames: ['plan-new'] },
  { to: '/profile', label: '我的', icon: 'profile', routeNames: ['profile'] },
]

function isActive(item: NavigationItem) {
  return item.routeNames.includes(String(route.name ?? ''))
}
</script>

<template>
  <nav class="mobile-navigation" aria-label="主要导航">
    <router-link
      v-for="item in items"
      :key="item.to"
      :to="item.to"
      class="mobile-navigation__item"
      :class="{ 'is-active': isActive(item) }"
      :aria-current="isActive(item) ? 'page' : undefined"
    >
      <PremiumIcon :name="item.icon" :size="18" :box-size="30" />
      <span>{{ item.label }}</span>
    </router-link>
  </nav>
</template>

<style scoped lang="scss">
.mobile-navigation { display: none; }

@media (max-width: 820px) {
  .mobile-navigation {
    position: fixed;
    inset: auto 0 0;
    z-index: $layer-mobile-nav;
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    min-height: 76px;
    padding: 5px 8px calc(5px + env(safe-area-inset-bottom));
    border-top: 1px solid rgba($color-brand, .16);
    background: rgba($color-surface, .97);
    box-shadow: 0 -12px 30px rgba($color-brand, .1);
    backdrop-filter: blur(18px) saturate(125%);
  }

  .mobile-navigation__item {
    position: relative;
    display: flex;
    min-width: 0;
    min-height: 64px;
    align-items: center;
    justify-content: center;
    flex-direction: column;
    gap: 2px;
    border-radius: $radius-md;
    color: $color-text-secondary;
    font-size: 12px;
    font-weight: 700;
  }

  .mobile-navigation__item::before {
    position: absolute;
    top: 4px;
    width: 22px;
    height: 3px;
    border-radius: $radius-round;
    background: $color-accent-strong;
    content: '';
    opacity: 0;
    transform: scaleX(.45);
    transition: opacity $motion-fast $ease-standard, transform $motion-fast $ease-standard;
  }

  .mobile-navigation__item.is-active {
    background: $color-surface-muted;
    color: $color-brand;
  }

  .mobile-navigation__item.is-active::before {
    opacity: 1;
    transform: scaleX(1);
  }

  .mobile-navigation__item :deep(.premium-icon) {
    border: 0;
    background: transparent;
    box-shadow: none;
    color: currentColor;
  }
}
</style>
