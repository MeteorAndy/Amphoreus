<script setup lang="ts">
import { ShieldCheck } from 'lucide-vue-next'
import { useI18n } from '../i18n'

const { currentLang } = useI18n()
const isZh = currentLang.value === 'zh'
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
          {{ isZh ? '叙事质量诊断报告 — 运行写作后查看' : 'Narrative quality diagnostics — run the writer to see reports' }}
        </p>
      </div>
    </header>

    <!-- Empty state placeholder -->
    <div class="folio p-12 text-center">
      <p class="text-parchment-dim text-sm leading-relaxed max-w-md mx-auto">
        {{ isZh
          ? '运行"叙事写作"或"一键生成"后，这里会展示全部 11 份诊断报告：套话扫描、Canon 校验、张力曲线、道具生命周期、读者模拟、token 预算、关系趋势、实体事件、图推断、自适应模式、叙事债务。'
          : 'After running the Writer or the Generate pipeline, all 11 diagnostic reports will appear here: cliche scan, canon verification, tension curve, prop lifecycle, reader simulation, token budget, relationship trends, entity events, graph inference, adaptive patterns, and narrative debt.' }}
      </p>
    </div>
  </div>
</template>
