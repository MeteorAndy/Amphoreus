<script setup lang="ts">
import { computed, type Component } from 'vue'
import {
  ShieldCheck, Type, CheckCircle, TrendingUp, Package,
  Eye, Coins, Heart, Activity, Network, Sparkle,
} from 'lucide-vue-next'
import { useI18n } from '../i18n'
import { useDiagnostics } from '../composables/useDiagnostics'
import TensionCurve from '../components/TensionCurve.vue'

const { currentLang } = useI18n()
const isZh = computed(() => currentLang.value === 'zh')
const { diagnostics, hasReports } = useDiagnostics()

interface ReportMeta {
  key: string
  zh: string
  en: string
  icon: Component
}

const REPORT_META: ReportMeta[] = [
  { key: 'cliche_report', zh: '套话扫描', en: 'Cliche Scan', icon: Type },
  { key: 'canon_report', zh: 'Canon 校验', en: 'Canon Verify', icon: CheckCircle },
  { key: 'tension_report', zh: '张力曲线', en: 'Tension Curve', icon: TrendingUp },
  { key: 'prop_lifecycle_report', zh: '道具生命周期', en: 'Prop Lifecycle', icon: Package },
  { key: 'reader_sim_report', zh: '读者模拟', en: 'Reader Sim', icon: Eye },
  { key: 'budget_report', zh: 'Token 预算', en: 'Token Budget', icon: Coins },
  { key: 'relationship_trend_report', zh: '关系趋势', en: 'Relationship Trend', icon: Heart },
  { key: 'entity_event_report', zh: '实体事件', en: 'Entity Events', icon: Activity },
  { key: 'graph_inference_report', zh: '图推断', en: 'Graph Inference', icon: Network },
  { key: 'adaptive_pattern_report', zh: '自适应模式', en: 'Adaptive Patterns', icon: Sparkle },
]

function reportSummary(key: string): { metric: string; level: 'pass' | 'warn' | 'fail' } {
  const d = diagnostics.value[key] as Record<string, unknown> | undefined
  if (!d) return { metric: '—', level: 'pass' }

  switch (key) {
    case 'cliche_report': {
      const score = (d.ai_flavor_score as number) ?? 0
      const hits = (d.hits as unknown[]) ?? []
      const level = score > 15 ? 'fail' : score > 5 ? 'warn' : 'pass'
      return { metric: isZh.value ? `${hits.length} 命中 · 分数 ${score.toFixed(1)}` : `${hits.length} hits · score ${score.toFixed(1)}`, level }
    }
    case 'canon_report': {
      const clean = d.clean as boolean
      const violations = (d.violations as unknown[]) ?? []
      return { metric: clean ? (isZh.value ? '✓ 无矛盾' : '✓ Clean') : `${violations.length} ${isZh.value ? '违例' : 'violations'}`, level: clean ? 'pass' : 'fail' }
    }
    case 'tension_report': {
      const chapters = (d.chapters as unknown[]) ?? []
      const flat = chapters.filter((c) => (c as Record<string, unknown>).flat).length
      return { metric: isZh.value ? `${chapters.length} 章 · ${flat} 平` : `${chapters.length} ch · ${flat} flat`, level: flat > chapters.length / 3 ? 'warn' : 'pass' }
    }
    case 'prop_lifecycle_report': {
      const props = (d.props as unknown[]) ?? []
      const unresolved = (d.unresolved as string[]) ?? []
      return { metric: isZh.value ? `${props.length} 道具 · ${unresolved.length} 悬置` : `${props.length} props · ${unresolved.length} unresolved`, level: unresolved.length > 0 ? 'warn' : 'pass' }
    }
    case 'reader_sim_report': {
      const retention = (d.predicted_retention as number) ?? 0
      const pct = Math.round(retention * 100)
      return { metric: isZh.value ? `留存 ${pct}%` : `Retention ${pct}%`, level: retention < 0.4 ? 'fail' : retention < 0.6 ? 'warn' : 'pass' }
    }
    case 'budget_report': {
      const total = (d.total_tokens as number) ?? 0
      const over = d.any_over as boolean
      return { metric: isZh.value ? `${total} tokens${over ? ' · 超限' : ''}` : `${total} tokens${over ? ' · over' : ''}`, level: over ? 'warn' : 'pass' }
    }
    case 'relationship_trend_report': {
      const pairs = (d.pairs as unknown[]) ?? []
      return { metric: isZh.value ? `${pairs.length} 对关系` : `${pairs.length} pairs`, level: 'pass' }
    }
    case 'entity_event_report': {
      const events = (d.events as unknown[]) ?? []
      return { metric: isZh.value ? `${events.length} 事件` : `${events.length} events`, level: 'pass' }
    }
    case 'graph_inference_report': {
      const facts = (d.facts as unknown[]) ?? []
      return { metric: isZh.value ? `${facts.length} 推断` : `${facts.length} facts`, level: 'pass' }
    }
    case 'adaptive_pattern_report': {
      const patterns = (d.patterns as unknown[]) ?? []
      const hits = (d.total_hits as number) ?? 0
      return { metric: isZh.value ? `${patterns.length} 模式 · ${hits} 命中` : `${patterns.length} patterns · ${hits} hits`, level: patterns.length > 3 ? 'warn' : 'pass' }
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
          {{ isZh ? '质量审稿台' : 'Quality Desk' }}
        </h1>
        <p class="text-sm text-muted mt-0.5">
          {{ hasReports
            ? (isZh ? '叙事质量诊断报告' : 'Narrative quality diagnostics')
            : (isZh ? '运行写作后查看报告' : 'Run the writer to see reports') }}
        </p>
      </div>
    </header>

    <!-- Reports grid -->
    <div v-if="hasReports" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      <div
        v-for="meta in REPORT_META.filter(m => diagnostics[m.key])"
        :key="meta.key"
        class="folio p-4 hover:border-ink-elevated transition-colors"
      >
        <div class="flex items-start justify-between mb-3">
          <div class="flex items-center gap-2">
            <component :is="meta.icon" :size="16" :stroke-width="1.5" class="text-parchment-dim" />
            <h3 class="text-sm font-medium text-parchment">
              {{ isZh ? meta.zh : meta.en }}
            </h3>
          </div>
          <span
            class="w-2 h-2 rounded-seal flex-shrink-0 mt-1"
            :class="`dot-${reportSummary(meta.key).level}`"
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
      class="folio p-4 mt-4"
    >
      <h3 class="text-sm font-medium text-parchment mb-3">
        {{ isZh ? '张力曲线' : 'Tension Curve' }}
      </h3>
      <TensionCurve :chapters="(diagnostics.tension_report as Record<string, unknown>).chapters as Array<Record<string, unknown>>" />
    </div>

    <!-- Empty state -->
    <div v-if="!hasReports" class="folio p-12 text-center">
      <ShieldCheck :size="32" :stroke-width="1" class="text-muted mx-auto mb-4" />
      <p class="text-parchment-dim text-sm leading-relaxed max-w-md mx-auto">
        {{ isZh
          ? '运行"叙事写作"或"一键生成"后，这里会展示全部诊断报告：套话扫描、Canon 校验、张力曲线、道具生命周期、读者模拟、token 预算、关系趋势、实体事件、图推断、自适应模式。'
          : 'After running the Writer or Generate pipeline, all diagnostic reports will appear here.' }}
      </p>
    </div>
  </div>
</template>
