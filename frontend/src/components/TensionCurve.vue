<script setup lang="ts">
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import { useTheme } from '../composables/useTheme'

use([CanvasRenderer, LineChart, GridComponent, TooltipComponent])

const props = defineProps<{
  chapters: Array<Record<string, unknown>>
}>()

const { theme } = useTheme()

const inkColors = {
  axisLine: '#2e2820',
  axisLabel: '#8a8070',
  tooltipBg: '#1c1814',
  tooltipBorder: '#2e2820',
  tooltipText: '#e8dfcf',
  line: '#c8423b',
  areaStart: 'rgba(200,66,59,0.25)',
  areaEnd: 'rgba(200,66,59,0)',
  flatMark: '#b8893c',
}

const paperColors = {
  axisLine: '#c9bda3',
  axisLabel: '#8a7f6e',
  tooltipBg: '#f0e7d5',
  tooltipBorder: '#c9bda3',
  tooltipText: '#1a1510',
  line: '#a8362f',
  areaStart: 'rgba(168,54,47,0.18)',
  areaEnd: 'rgba(168,54,47,0)',
  flatMark: '#9a7330',
}

const option = computed(() => {
  const colors = theme.value === 'paper' ? paperColors : inkColors
  const chs = props.chapters || []
  const labels = chs.map((c) => `Ch${c.chapter_number}`)
  const values = chs.map((c) => Number(c.tension) || 0)
  const flats = chs.map((c) => (c.flat ? 1 : 0))

  return {
    grid: { left: 36, right: 16, top: 12, bottom: 28 },
    xAxis: {
      type: 'category',
      data: labels,
      axisLine: { lineStyle: { color: colors.axisLine } },
      axisLabel: { color: colors.axisLabel, fontSize: 10 },
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: 1,
      splitLine: { lineStyle: { color: colors.axisLine } },
      axisLabel: { color: colors.axisLabel, fontSize: 10 },
    },
    tooltip: {
      trigger: 'axis',
      backgroundColor: colors.tooltipBg,
      borderColor: colors.tooltipBorder,
      textStyle: { color: colors.tooltipText, fontSize: 12 },
    },
    series: [
      {
        name: 'Tension',
        type: 'line',
        data: values,
        smooth: true,
        symbol: 'circle',
        symbolSize: 6,
        lineStyle: { color: colors.line, width: 2 },
        itemStyle: { color: colors.line },
        areaStyle: {
          color: {
            type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: colors.areaStart },
              { offset: 1, color: colors.areaEnd },
            ],
          },
        },
        markPoint: {
          data: flats.map((f, i) => f ? { xAxis: i, yAxis: values[i], itemStyle: { color: colors.flatMark } } : null).filter(Boolean),
        },
      },
    ],
  }
})
</script>

<template>
  <VChart :option="option" autoresize style="height: 240px; width: 100%;" />
</template>
