import assert from 'node:assert/strict'
import test from 'node:test'
import { reconcileExecution, validLegacyExecution } from '../src/utils/executionMigration.ts'

test('legacy records accept only valid non-pending meal slots', () => {
  assert.deepEqual(validLegacyExecution({
    'day:1:slot:breakfast': 'completed',
    'day:8:slot:lunch': 'skipped',
    'day:2:slot:snack': 'adjusted',
    'day:3:slot:dinner': 'pending',
  }), { 'day:1:slot:breakfast': 'completed' })
})

test('server-owned slots win and only missing local slots are offered for import', () => {
  const local = validLegacyExecution({
    'day:1:slot:breakfast': 'skipped',
    'day:1:slot:lunch': 'adjusted',
  })
  const reconciled = reconcileExecution(local, {
    plan_id: 1,
    events: [{ day: 1, meal_slot: 'breakfast', status: 'completed', note: null, updated_at: '2026-09-19' }],
  })
  assert.equal(reconciled.statuses['day:1:slot:breakfast'], 'completed')
  assert.deepEqual(reconciled.pendingImport, { 'day:1:slot:lunch': 'adjusted' })
  assert.equal(reconciled.conflictCount, 1)
})

test('an explicit planned server event still blocks old local status', () => {
  const reconciled = reconcileExecution({ 'day:1:slot:dinner': 'completed' }, {
    plan_id: 1,
    events: [{ day: 1, meal_slot: 'dinner', status: 'planned', note: null, updated_at: '2026-09-19' }],
  })
  assert.deepEqual(reconciled.pendingImport, {})
  assert.equal(reconciled.conflictCount, 1)
  assert.equal(reconciled.statuses['day:1:slot:dinner'], 'pending')
})
