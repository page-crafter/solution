<script setup lang="ts">
import { onMounted, onUnmounted, useTemplateRef } from 'vue'

const props = withDefaults(defineProps<{
  particleColor?: string
  speed?: number
  density?: number
  maxDistance?: number
}>(), {
  particleColor: '#888888',
  speed: 0.66,
  density: 10000,
  maxDistance: 120,
})

const canvasRef = useTemplateRef<HTMLCanvasElement>('canvas')

interface Particle {
  x: number
  y: number
  vx: number
  vy: number
}

let rafId = 0
let particles: Particle[] = []
let ctx: CanvasRenderingContext2D | null = null
let ro: ResizeObserver | null = null
let spawnTimer = 0

function spawnParticles(w: number, h: number): void {
  const count = Math.floor((w * h) / props.density)
  particles = Array.from({ length: count }, () => ({
    x: Math.random() * w,
    y: Math.random() * h,
    vx: (Math.random() - 0.5) * props.speed,
    vy: (Math.random() - 0.5) * props.speed,
  }))
}

function draw(): void {
  const canvas = canvasRef.value
  if (!canvas || !ctx) return
  const { width, height } = canvas

  ctx.clearRect(0, 0, width, height)

  for (let i = 0; i < particles.length; i++) {
    const p = particles[i]

    if (p.x > width + 20 || p.x < -20) p.vx = -p.vx
    if (p.y > height + 20 || p.y < -20) p.vy = -p.vy
    p.x += p.vx
    p.y += p.vy

    ctx.beginPath()
    ctx.fillStyle = props.particleColor
    ctx.globalAlpha = 0.7
    ctx.arc(p.x, p.y, 1.5, 0, Math.PI * 2)
    ctx.fill()

    for (let j = i + 1; j < particles.length; j++) {
      const q = particles[j]
      const dx = p.x - q.x
      const dy = p.y - q.y
      const dist = Math.sqrt(dx * dx + dy * dy)
      if (dist >= props.maxDistance) continue
      ctx.beginPath()
      ctx.strokeStyle = props.particleColor
      ctx.globalAlpha = (props.maxDistance - dist) / props.maxDistance
      ctx.lineWidth = 0.7
      ctx.moveTo(p.x, p.y)
      ctx.lineTo(q.x, q.y)
      ctx.stroke()
    }
  }

  rafId = requestAnimationFrame(draw)
}

onMounted(() => {
  const canvas = canvasRef.value
  if (!canvas) return
  ctx = canvas.getContext('2d')

  ro = new ResizeObserver((entries) => {
    const entry = entries[0]
    if (!entry) return
    const { width, height } = entry.contentRect
    canvas.width = Math.floor(width)
    canvas.height = Math.floor(height)
    clearTimeout(spawnTimer)
    spawnTimer = window.setTimeout(() => spawnParticles(canvas.width, canvas.height), 100)
  })
  ro.observe(canvas)

  rafId = requestAnimationFrame(draw)
})

onUnmounted(() => {
  cancelAnimationFrame(rafId)
  clearTimeout(spawnTimer)
  ro?.disconnect()
})
</script>

<template>
  <canvas ref="canvas" class="particle-bg" />
</template>

<style scoped>
.particle-bg {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  z-index: 0;
  pointer-events: none;
}
</style>
