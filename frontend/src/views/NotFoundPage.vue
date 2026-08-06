<template>
  <div class="not-found page-container">
    <span class="code">404</span>
    <h1>这个页面走丢了</h1>
    <p>地址可能已变化，返回首页继续创建你的饮食方案。</p>
    <el-button type="primary" size="large" round @click="$router.push('/')">返回首页</el-button>
  </div>
</template>

<style scoped lang="scss">
.not-found { min-height: 60vh; display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 64px 20px; text-align: center; }
.code { color: $color-sage; font-size: 64px; font-weight: 800; line-height: 1; }
h1 { margin-top: 12px; color: $color-text-primary; font-size: 28px; }
p { margin: 8px 0 24px; color: $color-text-secondary; }
</style>
