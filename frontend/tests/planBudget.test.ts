import assert from 'node:assert/strict'
import test from 'node:test'
import { explicitBudget } from '../src/utils/planBudget.ts'

test('a stated budget takes precedence and the latest revision wins', () => {
  assert.equal(explicitBudget('减脂一周，预算300元，预算改为200元'), 200)
  assert.equal(explicitBudget('总预算 0 元'), 0)
})

test('without a stated budget the numeric option remains available', () => {
  assert.equal(explicitBudget('减脂一周，不吃海鲜'), null)
  assert.equal(explicitBudget('不限制预算'), null)
})
