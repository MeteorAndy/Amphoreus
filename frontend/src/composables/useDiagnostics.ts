import { ref, computed } from 'vue'

/**
 * Shared reactive store for narrative-quality diagnostic reports.
 *
 * Module-level ref = singleton: usePipeline WRITES reports here on the WRITING
 * completed event, QualityView READS them. No Pinia/library needed — this is the
 * standard Vue 3 lightweight cross-component state pattern.
 */

export interface DiagnosticsData {
  cliche_report?: Record<string, unknown>
  canon_report?: Record<string, unknown>
  tension_report?: Record<string, unknown>
  prop_lifecycle_report?: Record<string, unknown>
  reader_sim_report?: Record<string, unknown>
  budget_report?: Record<string, unknown>
  relationship_trend_report?: Record<string, unknown>
  entity_event_report?: Record<string, unknown>
  graph_inference_report?: Record<string, unknown>
  adaptive_pattern_report?: Record<string, unknown>
  [key: string]: unknown
}

const diagnostics = ref<DiagnosticsData>({})
const hasReports = computed(() => Object.keys(diagnostics.value).length > 0)

function setReports(data: Record<string, unknown>): void {
  // Only capture known report keys that are non-empty (not {} or null).
  const reportKeys = [
    'cliche_report', 'canon_report', 'tension_report',
    'prop_lifecycle_report', 'reader_sim_report', 'budget_report',
    'relationship_trend_report', 'entity_event_report',
    'graph_inference_report', 'adaptive_pattern_report',
  ]
  const captured: DiagnosticsData = {}
  for (const key of reportKeys) {
    const val = data[key]
    if (val && typeof val === 'object' && Object.keys(val as object).length > 0) {
      captured[key] = val as Record<string, unknown>
    }
  }
  diagnostics.value = captured
}

function clear(): void {
  diagnostics.value = {}
}

export function useDiagnostics() {
  return { diagnostics, hasReports, setReports, clear }
}
