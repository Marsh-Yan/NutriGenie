import assert from 'node:assert/strict'
import test from 'node:test'
import { normalizePlanResult } from '../src/api/planResultAdapter.ts'

test('saved AI plans show daily macro averages instead of plan totals', () => {
  const days = Array.from({ length: 5 }, (_, index) => ({
    day: index + 1,
    meals: {},
    total_nutrition: { calories: 2253, protein_g: 122.6, fat_g: 67, carbs_g: 300.6, fiber_g: 25 },
  }))
  const result = normalizePlanResult({
    schema_version: 'ai_native_v2',
    recipes: [],
    weekly_plan: days,
    nutrition_report: {
      avg_daily_calories: 2253,
      total_calories: 11265,
      protein_g: 613,
      fat_g: 335,
      carbs_g: 1503,
      fiber_g: 125,
      recommendation: '保留原有建议',
    },
  })

  assert.equal(result?.nutrition_report.avg_daily_calories, 2253)
  assert.equal(result?.nutrition_report.protein_g, 122.6)
  assert.equal(result?.nutrition_report.fat_g, 67)
  assert.equal(result?.nutrition_report.carbs_g, 300.6)
  assert.equal(result?.nutrition_report.fiber_g, 25)
  assert.equal(result?.nutrition_report.recommendation, '保留原有建议')
})
