import { useRef, useCallback } from 'react'
import { gsap, useGSAP } from '../lib/gsap'

/**
 * 交错入场动画 — 一组元素依次出现
 */
export function useStaggerReveal(options?: {
  selector?: string
  stagger?: number
  duration?: number
  y?: number
  delay?: number
}) {
  const containerRef = useRef<HTMLDivElement>(null)
  const {
    selector = '.reveal-item',
    stagger = 0.1,
    duration = 0.5,
    y = 20,
    delay = 0,
  } = options || {}

  useGSAP(
    () => {
      gsap.from(selector, {
        opacity: 0,
        y,
        duration,
        stagger,
        delay,
        ease: 'power2.out',
      })
    },
    { scope: containerRef },
  )

  return containerRef
}

/**
 * 数字滚动动画 — 从 0 滚动到目标值
 */
export function useCountUp(endValue: number, options?: { duration?: number; decimals?: number }) {
  const ref = useRef<HTMLSpanElement>(null)
  const { duration = 1.2, decimals = 0 } = options || {}

  useGSAP(
    () => {
      if (!ref.current) return
      const obj = { value: 0 }
      gsap.to(obj, {
        value: endValue,
        duration,
        ease: 'power2.out',
        onUpdate: () => {
          if (ref.current) {
            ref.current.textContent = obj.value.toFixed(decimals)
          }
        },
      })
    },
    { dependencies: [endValue] },
  )

  return ref
}

/**
 * 光晕脉冲动画 — 持续的发光呼吸效果
 */
export function useGlowPulse(selector?: string) {
  const containerRef = useRef<HTMLDivElement>(null)

  useGSAP(
    () => {
      gsap.to(selector || '.glow-target', {
        boxShadow: '0 0 24px rgba(88,166,255,0.6)',
        duration: 1.5,
        repeat: -1,
        yoyo: true,
        ease: 'sine.inOut',
      })
    },
    { scope: containerRef },
  )

  return containerRef
}

/**
 * 入场时间线 — 页面/区块加载时的依次入场
 */
export function useEntryTimeline() {
  const containerRef = useRef<HTMLDivElement>(null)

  const createTimeline = useCallback(() => {
    return gsap.timeline({ defaults: { ease: 'power2.out' } })
  }, [])

  useGSAP(
    () => {
      // 时间线由各子组件通过 createTimeline 自行编排
    },
    { scope: containerRef },
  )

  return { containerRef, createTimeline }
}
