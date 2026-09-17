<script setup lang="ts">
import { useId } from 'vue'
import PremiumIcon from '@/components/common/PremiumIcon.vue'

defineProps<{
  title?: string
  message: string
  retryLabel?: string
}>()

const emit = defineEmits<{ retry: [] }>()
const titleId = useId()
</script>

<template>
  <section class="error-state" role="alert" :aria-labelledby="titleId">
    <PremiumIcon name="alert" :size="28" :box-size="56" />
    <div>
      <h2 :id="titleId">{{ title || '内容暂时无法加载' }}</h2>
      <p>{{ message }}</p>
    </div>
    <el-button v-if="retryLabel" type="primary" plain @click="emit('retry')">{{ retryLabel }}</el-button>
  </section>
</template>

<style scoped lang="scss">
.error-state {
  display: grid;
  max-width: 720px;
  justify-items: start;
  gap: $space-4;
  padding: clamp(24px, 4vw, 42px);
  border: 1px solid rgba($color-danger, .34);
  border-radius: $radius-lg;
  background: $color-surface-danger;
}

.error-state h2 { font-size: $text-xl; }
.error-state p { margin-top: $space-2; color: $color-text-secondary; }
</style>
