<script setup lang="ts">
import { type Component } from 'vue'
import {
  ShieldCheck, Type, CheckCircle, TrendingUp, Package,
  Eye, Coins, Heart, Activity, Network, Sparkle,
} from 'lucide-vue-next'
import { useI18n } from '../i18n'
import { useDiagnostics } from '../composables/useDiagnostics'
import TensionCurve from '../components/TensionCurve.vue'

const { t } = useI18n()
const { diagnostics, hasReports } = useDiagnostics()

interface ReportMeta {
  key: string
  icon: Component
}

const REPORT_META: ReportMeta[] = [
  { key: 'cliche_report', icon: Type },
  { key: 'canon_report', icon: CheckCircle },
  { key: 'tension_report', icon: TrendingUp },
  { key: 'prop_lifecycle_report', icon: Package },
  { key: 'reader_sim_report', icon: Eye },
  { key: 'budget_report', icon: Coins },
  { key: 'relationship_trend_report', icon: Heart },
  { key: 'entity_event_report', icon: Activity },
  { key: 'graph_inference_report', icon: Network },
  { key: 'adaptive_pattern_report', icon: Sparkle },
]

const dotColor = {
  pass: 'var(--color-editor)',
  warn: '#e8a838',
  fail: 'var(--color-danger)',
} as const

function reportSummary(key: string): { metric: string; level: 'pass' | 'warn' | 'fail' } {
  const d = diagnostics.value[key] as Record<string, unknown> | undefined
  if (!d) return { metric: '—', level: 'pass' }

  switch (key) {
    case 'cliche_report': {
      const score = (d.ai_flavor_score as number) ?? 0
      const hits = (d.hits as unknown[]) ?? []
      const level = score > 15 ? 'fail' : score > 5 ? 'warn' : 'pass'
      return { metric: t('quality.hits_score', { n: hits.length, s: score.toFixed(1) }), level }
    }
    case 'canon_report': {
      const clean = d.clean as boolean
      const violations = (d.violations as unknown[]) ?? []
      return { metric: clean ? t('quality.clean') : t('quality.violations', { n: violations.length }), level: clean ? 'pass' : 'fail' }
    }
    case 'tension_report': {
      const chapters = (d.chapters as unknown[]) ?? []
      const flat = chapters.filter((c) => (c as Record<string, unknown>).flat).length
      return { metric: t('quality.chapters_flat', { c: chapters.length, f: flat }), level: flat > chapters.length / 3 ? 'warn' : 'pass' }
    }
    case 'prop_lifecycle_report': {
      const props = (d.props as unknown[]) ?? []
      const unresolved = (d.unresolved as string[]) ?? []
      return { metric: t('quality.props_unresolved', { p: props.length, u: unresolved.length }), level: unresolved.length > 0 ? 'warn' : 'pass' }
    }
    case 'reader_sim_report': {
      const retention = (d.predicted_retention as number) ?? 0
      const pct = Math.round(retention * 100)
      return { metric: t('quality.retention', { p: pct }), level: retention < 0.4 ? 'fail' : retention < 0.6 ? 'warn' : 'pass' }
    }
    case 'budget_report': {
      const total = (d.total_tokens as number) ?? 0
      const over = d.any_over as boolean
      return { metric: over ? t('quality.tokens_over', { n: total }) : t('quality.tokens', { n: total }), level: over ? 'warn' : 'pass' }
    }
    case 'relationship_trend_report': {
      const pairs = (d.pairs as unknown[]) ?? []
      return { metric: t('quality.pairs', { n: pairs.length }), level: 'pass' }
    }
    case 'entity_event_report': {
      const events = (d.events as unknown[]) ?? []
      return { metric: t('quality.events', { n: events.length }), level: 'pass' }
    }
    case 'graph_inference_report': {
      const facts = (d.facts as unknown[]) ?? []
      return { metric: t('quality.facts', { n: facts.length }), level: 'pass' }
    }
    case 'adaptive_pattern_report': {
      const patterns = (d.patterns as unknown[]) ?? []
      const hits = (d.total_hits as number) ?? 0
      return { metric: t('quality.patterns_hits', { p: patterns.length, h: hits }), level: patterns.length > 3 ? 'warn' : 'pass' }
    }
    default:
      return { metric: '—', level: 'pass' }
  }
}
</script>

<template>
  <div class="space-y-6">
    <!-- Masthead -->
    <header class="flex items-center gap-3 pb-4 border-b border-ink-edge">
      <div class="w-10 h-10 rounded-seal bg-chop/15 border border-chop/40 flex items-center justify-center">
        <ShieldCheck :size="20" class="text-chop" :stroke-width="1.5" />
      </div>
      <div>
        <h1 class="text-xl text-parchment">
          {{ t('quality.title') }}
        </h1>
        <p class="text-sm text-muted mt-0.5">
          {{ hasReports ? t('quality.subtitle_ready') : t('quality.subtitle_empty') }}
        </p>
      </div>
    </header>

    <!-- Reports grid -->
    <div v-if="hasReports" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      <div
        v-for="meta in REPORT_META.filter(m => diagnostics[m.key])"
        :key="meta.key"
        class="card p-4 hover:border-ink-elevated transition-colors"
      >
        <div class="flex items-start justify-between mb-3">
          <div class="flex items-center gap-2">
            <component :is="meta.icon" :size="16" :stroke-width="1.5" class="text-parchment-dim" />
            <h3 class="text-sm font-medium text-parchment">
              {{ t(`quality.${meta.key}`) }}
            </h3>
          </div>
          <span
            class="w-2 h-2 rounded-full flex-shrink-0 mt-1"
            :style="{ backgroundColor: dotColor[reportSummary(meta.key).level] }"
          />
        </div>
        <p class="text-sm text-muted font-mono">
          {{ reportSummary(meta.key).metric }}
        </p>
      </div>
    </div>

    <!-- Tension curve visualization -->
    <div
      v-if="hasReports && (diagnostics.tension_report as Record<string, unknown> | undefined)?.chapters"
      class="card p-4 mt-4"
    >
      <h3 class="text-sm font-medium text-parchment mb-3">
        {{ t('quality.tension_curve') }}
      </h3>
      <TensionCurve :chapters="(diagnostics.tension_report as Record<string, unknown>).chapters as Array<Record<string, unknown>>" />
    </div>

    <!-- Empty state -->
    <div v-if="!hasReports" class="card p-12 text-center">
      <ShieldCheck :size="32" :stroke-width="1" class="text-muted mx-auto mb-4" />
      <p class="text-parchment-dim text-sm leading-relaxed max-w-md mx-auto">
        {{ t('quality.empty_desc') }}
      </p>
    </div>
  </div>
</template>
