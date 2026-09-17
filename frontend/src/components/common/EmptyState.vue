<script setup lang="ts">
import { useId } from 'vue'
import PremiumIcon from '@/components/common/PremiumIcon.vue'
import type { PremiumIconName } from '@/components/common/PremiumIcon.vue'

withDefaults(defineProps<{
  title: string
  description: string
  icon?: PremiumIconName
}>(), {
  icon: 'leaf',
})

const titleId = useId()
</script>

<template>
  <section class="empty-state" :aria-labelledby="titleId">
    <PremiumIcon :name="icon" :size="30" :box-size="60" />
    <div>
      <h2 :id="titleId">{{ title }}</h2>
      <p>{{ description }}</p>
    </div>
    <div v-if="$slots.actions" class="empty-state__actions">
      <slot name="actions" />
    </div>
  </section>
</template>

<style scoped lang="scss">
.empty-state {
  display: grid;
  max-width: 720px;
  justify-items: start;
  gap: $space-5;
  padding: clamp(28px, 5vw, 52px);
  border: 1px solid $color-border;
  border-left: 6px solid $color-accent-strong;
  border-radius: $radius-lg;
  background: $color-surface;
  box-shadow: $shadow-sm;
}

.empty-state :deep(.premium-icon) { border-radius: 50%; }
.empty-state h2 { font-size: clamp(1.45rem, 3vw, 2rem); letter-spacing: -.025em; }
.empty-state p { max-width: 58ch; margin-top: $space-2; color: $color-text-secondary; }
.empty-state__actions { display: flex; flex-wrap: wrap; gap: $space-3; }
</style>
