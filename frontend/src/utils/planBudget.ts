// Keep this pattern aligned with backend/app/workflow/nodes/intent_analyzer.py.
const BUDGET_PATTERN = /(?:总)?预算\s*(?:(?:改为|调整为|降至|降到|降低至|提高到|约|大概)\s*)?(\d+(?:\.\d+)?)\s*(?:元|块)?/g

export function explicitBudget(text: string): number | null {
  const matches = [...text.matchAll(BUDGET_PATTERN)]
  return matches.length ? Number(matches[matches.length - 1][1]) : null
}
