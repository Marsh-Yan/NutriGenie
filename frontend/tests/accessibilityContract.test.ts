import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import test from 'node:test'
import { fileURLToPath } from 'node:url'

const frontendRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..')

function read(relativePath: string) {
  return readFileSync(resolve(frontendRoot, relativePath), 'utf8')
}

test('viewport metadata keeps browser zoom available', () => {
  const html = read('index.html')
  assert.match(html, /name=["']viewport["'][^>]*width=device-width/)
  assert.doesNotMatch(html, /user-scalable\s*=\s*no/i)
  assert.doesNotMatch(html, /maximum-scale\s*=\s*1(?:\.0)?(?:[,"'])/i)
})

test('global motion contract disables delays and repeated motion', () => {
  const styles = read('src/assets/styles/global.scss')
  const reducedMotionBlock = styles.slice(styles.indexOf('@media (prefers-reduced-motion: reduce)'))

  assert.notEqual(reducedMotionBlock.length, 0)
  assert.match(reducedMotionBlock, /animation-delay:\s*0s\s*!important/)
  assert.match(reducedMotionBlock, /animation-duration:\s*\.01ms\s*!important/)
  assert.match(reducedMotionBlock, /animation-iteration-count:\s*1\s*!important/)
  assert.match(reducedMotionBlock, /transition-delay:\s*0s\s*!important/)
  assert.match(reducedMotionBlock, /transition-duration:\s*\.01ms\s*!important/)
  assert.match(reducedMotionBlock, /scroll-behavior:\s*auto\s*!important/)
})

test('router avoids smooth hash scrolling when reduced motion is requested', () => {
  const router = read('src/router/index.ts')
  assert.match(router, /matchMedia\(['"]\(prefers-reduced-motion: reduce\)['"]\)\.matches/)
  assert.match(router, /reducedMotion\s*\?\s*['"]instant['"]\s*:\s*['"]smooth['"]/)
})

test('narrow admin layouts keep edit and delete actions directly visible', () => {
  for (const page of ['src/views/AdminIngredientsPage.vue', 'src/views/AdminRecipesPage.vue']) {
    const source = read(page)
    assert.match(source, /class="desktop-table"/)
    assert.match(source, /class="mobile-data-list"/)
    assert.match(source, /class="mobile-card-actions"/)
    assert.match(source, /@media \(max-width: \$breakpoint-sm\)[\s\S]*\.desktop-table \{ display: none; \}/)
    assert.match(source, /\.mobile-card-actions :deep\(\.el-button\) \{[^}]*min-height: 44px/)
  }
})
