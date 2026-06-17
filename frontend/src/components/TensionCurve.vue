<script setup lang="ts">
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'

use([CanvasRenderer, LineChart, GridComponent, TooltipComponent])

const props = defineProps<{
  chapters: Array<Record<string, unknown>>
}>()

const option = computed(() => {
  const chs = props.chapters || []
  const labels = chs.map((c) => `Ch${c.chapter_number}`)
  const values = chs.map((c) => Number(c.tension) || 0)
  const flats = chs.map((c) => (c.flat ? 1 : 0))

  return {
    grid: { left: 36, right: 16, top: 12, bottom: 28 },
    xAxis: {
      type: 'category',
      data: labels,
      axisLine: { lineStyle: { color: '#2e2820' } },
      axisLabel: { color: '#8a8070', fontSize: 10 },
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: 1,
      splitLine: { lineStyle: { color: '#2e2820' } },
      axisLabel: { color: '#8a8070', fontSize: 10 },
    },
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#1c1814',
      borderColor: '#2e2820',
      textStyle: { color: '#e8dfcf', fontSize: 12 },
    },
    series: [
      {
        name: 'Tension',
        type: 'line',
        data: values,
        smooth: true,
        symbol: 'circle',
        symbolSize: 6,
        lineStyle: { color: '#c8423b', width: 2 },
        itemStyle: { color: '#c8423b' },
        areaStyle: {
          color: {
            type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(200,66,59,0.25)' },
              { offset: 1, color: 'rgba(200,66,59,0)' },
            ],
          },
        },
        markPoint: {
          data: flats.map((f, i) => f ? { xAxis: i, yAxis: values[i], itemStyle: { color: '#b8893c' } } : null).filter(Boolean),
        },
      },
    ],
  }
})
</script>

<template>
  <VChart :option="option" autoresize style="height: 200px; width: 100%;" />
</template>
