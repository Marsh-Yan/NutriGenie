import type { PlanStatus } from '@/types'

export interface LocalPlanIndexItem {
  planId: number
  title: string
  userInput: string
  durationDays: number
  totalBudget: number
  status: PlanStatus
  createdAt: string
  completedAt: string | null
  lastOpenedAt: string
  sourcePlanId?: number
}

export type MealExecutionStatus = 'pending' | 'completed' | 'adjusted' | 'skipped'

export interface MealExecutionState {
  statuses: Record<string, MealExecutionStatus>
}

export interface ShoppingCheckState {
  checkedKeys: string[]
}

export interface PantryState {
  items: string[]
}

export interface PreferenceState {
  note: string
}

export interface DashboardState {
  currentPlanId: number | null
}
