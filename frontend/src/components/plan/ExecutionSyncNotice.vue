<script setup lang="ts">
import { computed } from 'vue'
import { useExecutionStore } from '@/stores/execution'

const execution = useExecutionStore()
const pendingCount = computed(() => Object.keys(execution.pendingImport).length)

function discard() {
  if (window.confirm('放弃本设备的旧执行记录？服务端已有记录不会改变。')) execution.dismissLocal()
}
</script>

<template>
  <aside v-if="execution.loading || execution.error || pendingCount || execution.conflictCount" class="sync-notice" aria-live="polite">
    <p v-if="execution.loading">正在同步餐食执行记录…</p>
    <p v-if="execution.error" role="alert">同步未完成：{{ execution.error }}。请检查网络后重试。</p>
    <template v-if="execution.ready && (pendingCount || execution.conflictCount)">
      <p>
        本设备还有 {{ pendingCount }} 条旧执行记录未上传。
        <template v-if="execution.conflictCount">另有 {{ execution.conflictCount }} 条与服务端不同，已保留服务端版本。</template>
      </p>
      <p class="sync-detail">只有你选择“导入”后，未冲突的旧记录才会写入账户；已有服务端餐次不会被覆盖。</p>
    </template>
    <div class="sync-actions">
      <el-button v-if="execution.error" :loading="execution.loading" @click="execution.loadServer()">重试同步</el-button>
      <template v-if="execution.ready && (pendingCount || execution.conflictCount)">
        <el-button v-if="pendingCount" type="primary" :loading="execution.saving" @click="execution.importLocal()">导入未冲突记录</el-button>
        <el-button :disabled="execution.saving" @click="discard">放弃本机旧记录</el-button>
      </template>
    </div>
  </aside>
</template>

<style scoped lang="scss">
.sync-notice {
  display: grid;
  gap: 8px;
  margin: 16px 0;
  padding: 16px 20px;
  border: 1px solid $color-border;
  border-radius: 14px;
  background: $color-surface-soft;
  color: $color-text-primary;
  font-size: 15px;
  line-height: 1.55;
}
.sync-detail { color: $color-text-secondary; }
.sync-actions { display: flex; flex-wrap: wrap; gap: 8px; }
.sync-actions .el-button { margin: 0; min-height: 44px; }
</style>
