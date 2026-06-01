import { useRef, useEffect } from 'react'
import { gsap } from '../lib/gsap'

interface Particle {
  x: number
  y: number
  vx: number
  vy: number
  radius: number
  opacity: number
}

/**
 * 科技感粒子背景 — 连线粒子效果
 * 粒子缓慢漂移，距离近的粒子之间画连线，鼠标靠近时粒子散开
 */
export default function ParticleField() {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext('2d')!
    let width = 0
    let height = 0
    let particles: Particle[] = []
    let mouseX = -9999
    let mouseY = -9999
    let rafId: number

    const PARTICLE_COUNT = 60
    const CONNECT_DIST = 120
    const MOUSE_RADIUS = 100

    function resize() {
      const parent = canvas!.parentElement!
      width = parent.clientWidth
      height = parent.clientHeight
      canvas!.width = width * devicePixelRatio
      canvas!.height = height * devicePixelRatio
      canvas!.style.width = `${width}px`
      canvas!.style.height = `${height}px`
      ctx.scale(devicePixelRatio, devicePixelRatio)
    }

    function initParticles() {
      particles = Array.from({ length: PARTICLE_COUNT }, () => ({
        x: Math.random() * width,
        y: Math.random() * height,
        vx: (Math.random() - 0.5) * 0.4,
        vy: (Math.random() - 0.5) * 0.4,
        radius: Math.random() * 1.5 + 0.5,
        opacity: Math.random() * 0.5 + 0.2,
      }))
    }

    function draw() {
      ctx.clearRect(0, 0, width, height)

      // 更新粒子位置
      for (const p of particles) {
        // 鼠标排斥力
        const dx = p.x - mouseX
        const dy = p.y - mouseY
        const dist = Math.sqrt(dx * dx + dy * dy)
        if (dist < MOUSE_RADIUS && dist > 0) {
          const force = (MOUSE_RADIUS - dist) / MOUSE_RADIUS * 0.8
          p.vx += (dx / dist) * force
          p.vy += (dy / dist) * force
        }

        // 速度衰减
        p.vx *= 0.98
        p.vy *= 0.98

        p.x += p.vx
        p.y += p.vy

        // 边界反弹
        if (p.x < 0 || p.x > width) p.vx *= -1
        if (p.y < 0 || p.y > height) p.vy *= -1
        p.x = Math.max(0, Math.min(width, p.x))
        p.y = Math.max(0, Math.min(height, p.y))
      }

      // 画连线
      for (let i = 0; i < particles.length; i++) {
        for (let j = i + 1; j < particles.length; j++) {
          const a = particles[i]
          const b = particles[j]
          const dx = a.x - b.x
          const dy = a.y - b.y
          const dist = Math.sqrt(dx * dx + dy * dy)
          if (dist < CONNECT_DIST) {
            const alpha = (1 - dist / CONNECT_DIST) * 0.15
            ctx.beginPath()
            ctx.moveTo(a.x, a.y)
            ctx.lineTo(b.x, b.y)
            ctx.strokeStyle = `rgba(88, 166, 255, ${alpha})`
            ctx.lineWidth = 0.5
            ctx.stroke()
          }
        }
      }

      // 画粒子
      for (const p of particles) {
        ctx.beginPath()
        ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2)
        ctx.fillStyle = `rgba(88, 166, 255, ${p.opacity})`
        ctx.fill()
      }

      rafId = requestAnimationFrame(draw)
    }

    function onMouseMove(e: MouseEvent) {
      const rect = canvas!.getBoundingClientRect()
      mouseX = e.clientX - rect.left
      mouseY = e.clientY - rect.top
    }

    function onMouseLeave() {
      mouseX = -9999
      mouseY = -9999
    }

    resize()
    initParticles()

    // 用 GSAP ticker 驱动动画帧（更高效）
    const tickerCallback = () => draw()
    gsap.ticker.add(tickerCallback)

    window.addEventListener('resize', resize)
    canvas.addEventListener('mousemove', onMouseMove)
    canvas.addEventListener('mouseleave', onMouseLeave)

    return () => {
      gsap.ticker.remove(tickerCallback)
      cancelAnimationFrame(rafId)
      window.removeEventListener('resize', resize)
      canvas.removeEventListener('mousemove', onMouseMove)
      canvas.removeEventListener('mouseleave', onMouseLeave)
    }
  }, [])

  return (
    <canvas
      ref={canvasRef}
      className="absolute inset-0 pointer-events-auto"
      style={{ opacity: 0.6 }}
    />
  )
}
