<script setup lang="ts">
defineProps<{
  title: string
  description?: string
  kicker?: string
}>()
</script>

<template>
  <header class="page-heading">
    <div class="page-heading__copy">
      <span v-if="kicker" class="page-heading__kicker">{{ kicker }}</span>
      <h1>{{ title }}</h1>
      <p v-if="description">{{ description }}</p>
    </div>
    <div v-if="$slots.actions" class="page-heading__actions">
      <slot name="actions" />
    </div>
  </header>
</template>

<style scoped lang="scss">
.page-heading {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: $space-6;
  padding-block: clamp(34px, 6vw, 72px) $space-6;
  border-bottom: 1px solid $color-divider;
}

.page-heading__copy { max-width: 720px; }
.page-heading__kicker { color: $color-brand; font-size: $text-sm; font-weight: 760; }
.page-heading h1 { margin-top: $space-2; font-size: $text-2xl; letter-spacing: -.035em; }
.page-heading p { max-width: 65ch; margin-top: $space-3; color: $color-text-secondary; }
.page-heading__actions { display: flex; flex: 0 0 auto; gap: $space-3; }

@media (max-width: $breakpoint-md) {
  .page-heading { align-items: flex-start; flex-direction: column; }
  .page-heading__actions { width: 100%; }
}
</style>
