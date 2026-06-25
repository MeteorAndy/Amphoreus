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

type ReportTone = 'chop' | 'editor' | 'gold' | 'ink'

interface ReportMeta {
  key: string
  icon: Component
  tone: ReportTone
}

const REPORT_META: ReportMeta[] = [
  { key: 'cliche_report', icon: Type, tone: 'chop' },
  { key: 'canon_report', icon: CheckCircle, tone: 'editor' },
  { key: 'tension_report', icon: TrendingUp, tone: 'gold' },
  { key: 'prop_lifecycle_report', icon: Package, tone: 'gold' },
  { key: 'reader_sim_report', icon: Eye, tone: 'chop' },
  { key: 'budget_report', icon: Coins, tone: 'gold' },
  { key: 'relationship_trend_report', icon: Heart, tone: 'editor' },
  { key: 'entity_event_report', icon: Activity, tone: 'ink' },
  { key: 'graph_inference_report', icon: Network, tone: 'chop' },
  { key: 'adaptive_pattern_report', icon: Sparkle, tone: 'gold' },
]

const toneMap = {
  chop: {
    bg: 'var(--color-chop-soft)',
    border: 'var(--color-chop-border)',
    text: 'var(--color-chop-light)',
    gradient: 'var(--gradient-chop-seal)',
    glow: 'var(--color-chop-glow)',
  },
  editor: {
    bg: 'var(--color-editor-soft)',
    border: 'rgba(90, 138, 79, 0.35)',
    text: 'var(--color-editor-light)',
    gradient: 'var(--gradient-editor-seal)',
    glow: 'rgba(90, 138, 79, 0.2)',
  },
  gold: {
    bg: 'var(--color-gold-soft)',
    border: 'rgba(201, 148, 74, 0.35)',
    text: 'var(--color-gold-light)',
    gradient: 'var(--gradient-gold-seal)',
    glow: 'rgba(201, 148, 74, 0.2)',
  },
  ink: {
    bg: 'var(--color-ink-wash-light)',
    border: 'var(--color-ink-edge)',
    text: 'var(--color-parchment-dim)',
    gradient: 'linear-gradient(135deg, var(--color-parchment-dim), var(--color-muted))',
    glow: 'rgba(0,0,0,0.1)',
  },
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
  <div class="quality-view fade-in-up">
    <!-- Masthead - Page header style -->
    <header class="quality-masthead">
      <div class="masthead-inner">
        <div class="masthead-seal seal-glow">
          <div class="seal-gradient">
            <ShieldCheck :size="22" class="seal-icon" :stroke-width="1.5" />
          </div>
        </div>
        <div class="masthead-text">
          <h1 class="masthead-title font-display">
            {{ t('quality.title') }}
          </h1>
          <p class="masthead-subtitle">
            {{ hasReports ? t('quality.subtitle_ready') : t('quality.subtitle_empty') }}
          </p>
        </div>
      </div>
      <div class="rule-ornament rule-ornament-diamond masthead-rule">
        <span class="rule-diamond">◆</span>
      </div>
    </header>

    <!-- Reports grid -->
    <div v-if="hasReports" class="reports-grid stagger-children">
      <article
        v-for="meta in REPORT_META.filter(m => diagnostics[m.key])"
        :key="meta.key"
        class="report-card"
        :data-tone="meta.tone"
      >
        <div class="card-color-bar" :style="{ background: toneMap[meta.tone].gradient }" />
        <div class="card-body">
          <div class="card-header">
            <div class="card-icon-wrap" :style="{ background: toneMap[meta.tone].bg, borderColor: toneMap[meta.tone].border }">
              <component 
                :is="meta.icon" 
                :size="16" 
                :stroke-width="1.5" 
                :style="{ color: toneMap[meta.tone].text }" 
              />
            </div>
            <h3 class="card-title font-display">
              {{ t(`quality.${meta.key}`) }}
            </h3>
            <span 
              class="status-dot"
              :class="`dot-${reportSummary(meta.key).level}`"
            />
          </div>
          <p class="card-metric font-display">
            {{ reportSummary(meta.key).metric }}
          </p>
        </div>
      </article>
    </div>

    <!-- Tension curve visualization -->
    <article
      v-if="hasReports && (diagnostics.tension_report as Record<string, unknown> | undefined)?.chapters"
      class="tension-card card"
    >
      <header class="tension-header">
        <div class="tension-title-wrap">
          <div class="tension-icon gold-icon-wrap">
            <TrendingUp :size="18" :stroke-width="1.5" class="text-gold-light" />
          </div>
          <h3 class="tension-title font-display">
            {{ t('quality.tension_curve') }}
          </h3>
        </div>
      </header>
      <div class="tension-chart-wrap">
        <TensionCurve :chapters="(diagnostics.tension_report as Record<string, unknown>).chapters as Array<Record<string, unknown>>" />
      </div>
    </article>

    <!-- Empty state -->
    <div v-if="!hasReports" class="empty-state">
      <div class="empty-icon-wrap">
        <ShieldCheck :size="56" :stroke-width="1" class="empty-icon" />
      </div>
      <div class="empty-rule" />
      <p class="empty-text">
        {{ t('quality.empty_desc') }}
      </p>
      <div class="empty-rule" />
    </div>
  </div>
</template>

<style scoped>
.quality-view {
  max-width: 100%;
}

/* ═══════════════════════════════════════════════════════════════════════
   Masthead - Page header style with seal
   ═══════════════════════════════════════════════════════════════════════ */
.quality-masthead {
  margin-bottom: var(--space-section);
}

.masthead-inner {
  display: flex;
  align-items: center;
  gap: var(--space-block);
  padding-bottom: var(--space-block);
}

.masthead-seal {
  flex-shrink: 0;
  width: 52px;
  height: 52px;
  border-radius: var(--radius-seal);
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
}

.seal-gradient {
  width: 44px;
  height: 44px;
  border-radius: var(--radius-seal);
  background: var(--gradient-chop-seal);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: inset 0 2px 4px rgba(255,255,255,0.2),
              inset 0 -2px 4px rgba(0,0,0,0.2);
  position: relative;
}

.seal-icon {
  color: #fff;
  text-shadow: 0 1px 1px rgba(0,0,0,0.3);
}

.masthead-text {
  flex: 1;
  min-width: 0;
}

.masthead-title {
  font-size: var(--text-3xl);
  font-weight: 700;
  letter-spacing: -0.02em;
  color: var(--color-parchment-bright);
  margin: 0;
  line-height: 1.2;
}

.masthead-subtitle {
  font-size: var(--text-base);
  color: var(--color-parchment-muted);
  margin: var(--space-compact) 0 0;
  font-style: italic;
  font-family: var(--font-display);
  opacity: 0.8;
}

.masthead-rule {
  color: var(--color-chop);
  font-size: var(--text-xs);
  opacity: 0.6;
}

.rule-diamond {
  letter-spacing: 0.5em;
  padding: 0 0.25em;
}

/* ═══════════════════════════════════════════════════════════════════════
   Reports grid
   ═══════════════════════════════════════════════════════════════════════ */
.reports-grid {
  display: grid;
  grid-template-columns: repeat(1, minmax(0, 1fr));
  gap: var(--space-block);
  margin-bottom: var(--space-section);
}

@media (min-width: 640px) {
  .reports-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (min-width: 1024px) {
  .reports-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

.report-card {
  background: var(--color-ink-panel);
  background-image: linear-gradient(180deg, rgba(237, 228, 211, 0.03) 0%, rgba(237, 228, 211, 0.01) 40%, transparent 100%);
  border: 1px solid var(--color-ink-edge);
  border-radius: var(--radius-card);
  box-shadow: var(--shadow-card),
              var(--shadow-inset);
  position: relative;
  overflow: hidden;
  transition: border-color var(--duration-fast) var(--ease-editorial),
              box-shadow var(--duration-fast) var(--ease-editorial),
              transform var(--duration-fast) var(--ease-editorial);
  isolation: isolate;
}

.report-card::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: inherit;
  background: linear-gradient(180deg, rgba(255,255,255,0.04) 0%, transparent 30%);
  pointer-events: none;
  z-index: -1;
}

.report-card:hover {
  transform: translateY(-3px);
}

.report-card[data-tone="chop"]:hover {
  border-color: var(--color-chop-border);
  box-shadow: 0 6px 20px rgba(200, 66, 59, 0.15),
              var(--shadow-elevated),
              var(--shadow-inset);
}

.report-card[data-tone="editor"]:hover {
  border-color: rgba(90, 138, 79, 0.4);
  box-shadow: 0 6px 20px rgba(90, 138, 79, 0.12),
              var(--shadow-elevated),
              var(--shadow-inset);
}

.report-card[data-tone="gold"]:hover {
  border-color: rgba(201, 148, 74, 0.4);
  box-shadow: 0 6px 20px rgba(201, 148, 74, 0.12),
              var(--shadow-elevated),
              var(--shadow-inset);
}

.report-card[data-tone="ink"]:hover {
  border-color: var(--color-ink-highlight);
  box-shadow: var(--shadow-elevated),
              var(--shadow-inset);
}

.card-color-bar {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  opacity: 0.85;
}

.card-body {
  padding: var(--space-block);
  padding-top: calc(var(--space-block) + 3px);
}

.card-header {
  display: flex;
  align-items: center;
  gap: var(--space-element);
  margin-bottom: var(--space-element);
}

.card-icon-wrap {
  width: 32px;
  height: 32px;
  border-radius: var(--radius-seal);
  border: 1px solid;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.card-title {
  flex: 1;
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--color-parchment);
  margin: 0;
  letter-spacing: 0.01em;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.status-dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  flex-shrink: 0;
}

.card-metric {
  font-size: var(--text-lg);
  font-weight: 500;
  color: var(--color-parchment-dim);
  margin: 0;
  letter-spacing: -0.01em;
  line-height: 1.4;
}

/* ═══════════════════════════════════════════════════════════════════════
   Tension curve card
   ═══════════════════════════════════════════════════════════════════════ */
.tension-card {
  padding: var(--space-block);
  margin-bottom: var(--space-section);
}

.tension-header {
  margin-bottom: var(--space-block);
}

.tension-title-wrap {
  display: flex;
  align-items: center;
  gap: var(--space-element);
}

.gold-icon-wrap {
  width: 36px;
  height: 36px;
  border-radius: var(--radius-seal);
  background: var(--color-gold-soft);
  border: 1px solid rgba(201, 148, 74, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
}

.tension-title {
  font-size: var(--text-lg);
  font-weight: 600;
  color: var(--color-parchment);
  margin: 0;
}

.tension-chart-wrap {
  min-height: 240px;
  position: relative;
}

/* ═══════════════════════════════════════════════════════════════════════
   Empty state
   ═══════════════════════════════════════════════════════════════════════ */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 4rem 1rem;
  text-align: center;
  color: var(--color-muted);
  position: relative;
}

.empty-icon-wrap {
  width: 88px;
  height: 88px;
  border-radius: var(--radius-seal);
  background: var(--color-ink-wash-light);
  border: 1px solid var(--color-ink-edge);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: var(--space-block);
  opacity: 0.6;
}

.empty-icon {
  color: var(--color-parchment-dim);
}

.empty-rule {
  width: 80px;
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--color-ink-edge), transparent);
}

.empty-rule:first-of-type {
  margin-bottom: var(--space-block);
}

.empty-rule:last-of-type {
  margin-top: var(--space-block);
}

.empty-text {
  font-size: var(--text-base);
  color: var(--color-parchment-muted);
  max-width: 42ch;
  line-height: 1.8;
  margin: 0;
  font-family: var(--font-display);
  font-style: italic;
}

/* ═══════════════════════════════════════════════════════════════════════
   Paper theme (light mode) adjustments
   ═══════════════════════════════════════════════════════════════════════ */
:global(html[data-theme="paper"]) .report-card {
  background: var(--color-paper-cream);
  background-image: linear-gradient(180deg, rgba(255,255,255,0.5) 0%, rgba(255,255,255,0.15) 40%, transparent 100%);
  box-shadow: var(--shadow-card-paper),
              var(--shadow-inset-paper);
  border-color: var(--color-paper-edge-soft);
}

:global(html[data-theme="paper"]) .report-card::before {
  background: linear-gradient(180deg, rgba(255,255,255,0.6) 0%, transparent 30%);
}

:global(html[data-theme="paper"]) .report-card[data-tone="chop"]:hover {
  box-shadow: 0 6px 20px rgba(168, 54, 47, 0.12),
              var(--shadow-elevated-paper),
              var(--shadow-inset-paper);
}

:global(html[data-theme="paper"]) .report-card[data-tone="editor"]:hover {
  box-shadow: 0 6px 20px rgba(61, 107, 50, 0.1),
              var(--shadow-elevated-paper),
              var(--shadow-inset-paper);
}

:global(html[data-theme="paper"]) .report-card[data-tone="gold"]:hover {
  box-shadow: 0 6px 20px rgba(154, 115, 48, 0.1),
              var(--shadow-elevated-paper),
              var(--shadow-inset-paper);
}

:global(html[data-theme="paper"]) .masthead-title {
  color: var(--color-ink-on-paper);
}

:global(html[data-theme="paper"]) .masthead-subtitle {
  color: var(--color-ink-on-paper-muted);
}

:global(html[data-theme="paper"]) .card-title {
  color: var(--color-ink-on-paper);
}

:global(html[data-theme="paper"]) .card-metric {
  color: var(--color-ink-on-paper-dim);
}

:global(html[data-theme="paper"]) .tension-title {
  color: var(--color-ink-on-paper);
}

:global(html[data-theme="paper"]) .empty-icon-wrap {
  background: rgba(26, 21, 16, 0.03);
  border-color: var(--color-paper-edge);
}

:global(html[data-theme="paper"]) .empty-icon {
  color: var(--color-ink-on-paper-dim);
}

:global(html[data-theme="paper"]) .empty-text {
  color: var(--color-ink-on-paper-muted);
}

:global(html[data-theme="paper"]) .empty-rule {
  background: linear-gradient(90deg, transparent, var(--color-paper-edge), transparent);
}
</style>
