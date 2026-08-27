<template>
  <div class="not-found page-container">
    <div class="not-found-card">
      <div class="visual" aria-hidden="true"><span>4</span><i>🥗</i><span>4</span></div>
      <span class="kicker">PAGE NOT FOUND</span>
      <h1>这份菜单里没有这一页。</h1>
      <p>地址可能已经变化。不如回到首页，继续规划下一顿好好吃饭。</p>
      <el-button type="primary" size="large" round @click="$router.push('/')">返回首页</el-button>
    </div>
  </div>
</template>

<style scoped lang="scss">
.not-found { display: grid; place-items: center; min-height: 66vh; padding-top: 48px; padding-bottom: 48px; text-align: center; }
.not-found-card { width: min(100%, 720px); padding: clamp(40px,7vw,76px); border: 1px solid rgba($color-sage-dark,.1); border-radius: $radius-xl; background: rgba(255,255,255,.82); box-shadow: $shadow-md; }
.visual { display: flex; align-items: center; justify-content: center; gap: 12px; color: $color-sage-dark; font-size: clamp(56px,9vw,92px); font-weight: 900; letter-spacing: -.08em; line-height: 1; }
.visual i { display: grid; place-items: center; width: clamp(72px,10vw,108px); height: clamp(72px,10vw,108px); border-radius: 34%; background: $color-lime-soft; font-size: clamp(36px,5vw,54px); font-style: normal; transform: rotate(-6deg); }
.kicker { display: block; margin-top: 28px; color: $color-sage; font-size: 10px; font-weight: 850; letter-spacing: .14em; }
h1 { margin-top: 8px; font-size: clamp(28px,4vw,42px); letter-spacing: -.04em; }
p { max-width: 500px; margin: 12px auto 28px; color: $color-text-secondary; }
</style>
