/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // 深色专业蓝灰基调
        background: {
          DEFAULT: '#0a0e14',
          panel: '#12171f',
          card: '#1a1f2b',
          input: '#0d1117',
          hover: '#1f2937',
        },
        surface: {
          50: '#e6edf3',
          100: '#c9d1d9',
          200: '#8b949e',
          300: '#6e7681',
          400: '#484f58',
          500: '#30363d',
          600: '#21262d',
          700: '#161b22',
          800: '#0d1117',
          900: '#0a0e14',
        },
        // 科技感强调色
        accent: {
          cyan: '#58a6ff',
          purple: '#a371f7',
          green: '#3fb950',
          orange: '#d29922',
          red: '#f85149',
          teal: '#39d2c0',
        },
        // Agent 专属色板
        agent: {
          pm: '#58a6ff',
          architect: '#a371f7',
          backend: '#3fb950',
          frontend: '#f0883e',
          tester: '#f85149',
          devops: '#39d2c0',
        },
        primary: {
          50: '#f0f9ff',
          100: '#e0f2fe',
          200: '#bae6fd',
          300: '#7dd3fc',
          400: '#38bdf8',
          500: '#58a6ff',
          600: '#388bfd',
          700: '#1f6feb',
          800: '#1158c7',
          900: '#0d419d',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'Consolas', 'monospace'],
      },
      animation: {
        'pulse-glow': 'pulseGlow 2s ease-in-out infinite',
        'slide-up': 'slideUp 0.3s ease-out',
        'slide-down': 'slideDown 0.3s ease-out',
        'fade-in': 'fadeIn 0.2s ease-out',
        'flow-line': 'flowLine 1.5s linear infinite',
        'blink': 'blink 1s step-end infinite',
        'spin-slow': 'spin 3s linear infinite',
        'shimmer': 'shimmer 2s linear infinite',
      },
      keyframes: {
        pulseGlow: {
          '0%, 100%': { boxShadow: '0 0 4px rgba(88,166,255,0.4)' },
          '50%': { boxShadow: '0 0 16px rgba(88,166,255,0.8)' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(8px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        slideDown: {
          '0%': { opacity: '0', transform: 'translateY(-8px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        flowLine: {
          '0%': { backgroundPosition: '0% 0%' },
          '100%': { backgroundPosition: '0% 100%' },
        },
        blink: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0' },
        },
        shimmer: {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
      },
      boxShadow: {
        'glow-cyan': '0 0 12px rgba(88,166,255,0.3)',
        'glow-green': '0 0 12px rgba(63,185,80,0.3)',
        'glow-red': '0 0 12px rgba(248,81,73,0.3)',
        'glow-purple': '0 0 12px rgba(163,113,247,0.3)',
        'panel': '0 4px 24px rgba(0,0,0,0.4)',
      },
    },
  },
  plugins: [],
}
