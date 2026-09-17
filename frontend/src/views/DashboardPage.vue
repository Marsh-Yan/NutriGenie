<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import EmptyState from '@/components/common/EmptyState.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()
const displayName = computed(() => auth.user?.nickname || '你好')
</script>

<template>
  <div class="dashboard-page page-container">
    <PageHeader
      kicker="今日安排"
      :title="`${displayName}，从下一餐开始执行计划。`"
      description="从已有计划继续今天的安排，或者根据当前目标、预算和忌口创建一份新计划。"
    >
      <template #actions>
        <el-button type="primary" @click="router.push('/plan/new')">创建计划</el-button>
      </template>
    </PageHeader>

    <div class="dashboard-page__content">
      <EmptyState
        icon="timeline"
        title="从一份计划开始今天的安排"
        description="打开已有计划查看完整餐单，或者创建一份符合当前目标、预算和忌口的新计划。"
      >
        <template #actions>
          <el-button type="primary" @click="router.push('/plans')">查看我的计划</el-button>
          <el-button @click="router.push('/plan/new')">创建新计划</el-button>
        </template>
      </EmptyState>
    </div>
  </div>
</template>

<style scoped lang="scss">
.dashboard-page { padding-bottom: clamp(72px, 10vw, 120px); }
.dashboard-page__content { padding-top: clamp(32px, 6vw, 64px); }
</style>
