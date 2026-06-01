import { gsap } from 'gsap'
import { useGSAP } from '@gsap/react'

// 注册 React hook 插件
gsap.registerPlugin(useGSAP)

// 全局默认配置 — 科技感动画风格
gsap.defaults({
  ease: 'power2.out',
  duration: 0.6,
})

export { gsap, useGSAP }
