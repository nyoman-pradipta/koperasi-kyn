<script setup>
import { computed } from 'vue'

const props = defineProps({
  labels: { type: Array, default: () => [] },
  masuk: { type: Array, default: () => [] },
  keluar: { type: Array, default: () => [] },
})

const W = 560
const H = 220
const pad = { l: 8, r: 8, t: 10, b: 26 }

const max = computed(() =>
  Math.max(1, ...props.masuk, ...props.keluar)
)

const groups = computed(() => {
  const n = props.labels.length || 1
  const gw = (W - pad.l - pad.r) / n
  const bw = Math.min(18, gw / 3)
  const innerH = H - pad.t - pad.b
  return props.labels.map((label, i) => {
    const x = pad.l + gw * i + gw / 2
    const hIn = (props.masuk[i] / max.value) * innerH
    const hOut = (props.keluar[i] / max.value) * innerH
    const base = H - pad.b
    return {
      label,
      x,
      bw,
      in: { x: x - bw - 1, y: base - hIn, h: hIn },
      out: { x: x + 1, y: base - hOut, h: hOut },
    }
  })
})
</script>

<template>
  <div class="chart">
    <svg :viewBox="`0 0 ${W} ${H}`" preserveAspectRatio="xMidYMid meet">
      <line :x1="pad.l" :y1="H - pad.b" :x2="W - pad.r" :y2="H - pad.b" stroke="var(--border)" />
      <g v-for="g in groups" :key="g.label">
        <rect :x="g.in.x" :y="g.in.y" :width="g.bw" :height="g.in.h" rx="2" fill="var(--primary)" />
        <rect :x="g.out.x" :y="g.out.y" :width="g.bw" :height="g.out.h" rx="2" fill="#d97706" />
        <text :x="g.x" :y="H - 8" text-anchor="middle" font-size="10" fill="var(--muted)">{{ g.label }}</text>
      </g>
    </svg>
    <div class="legend">
      <span><i class="sq in"></i> Kas Masuk</span>
      <span><i class="sq out"></i> Kas Keluar</span>
    </div>
  </div>
</template>

<style scoped>
.chart { width: 100%; }
svg { width: 100%; height: auto; }
.legend { display: flex; gap: 18px; justify-content: center; font-size: 0.8rem; color: var(--muted); margin-top: 6px; }
.sq { display: inline-block; width: 10px; height: 10px; border-radius: 2px; margin-right: 4px; }
.sq.in { background: var(--primary); }
.sq.out { background: #d97706; }
</style>
