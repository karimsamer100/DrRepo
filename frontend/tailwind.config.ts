import type { Config } from 'tailwindcss'

const config: Config = {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        base: '#0b0f17',
        panel: '#0e1420',
        surface: '#121826',
        'surface-2': '#1a2233',
        raised: '#1a2332',
        border: '#243044',
        brand: {
          DEFAULT: '#22d3ee',
          hover: '#06b6d4',
        },
        health: {
          DEFAULT: '#22c55e',
          dim: '#15803d',
        },
        attention: '#eab308',
        warning: '#f59e0b',
        error: '#ef4444',
        critical: '#dc2626',
        muted: '#94a3b8',
        faint: '#7c8aa0',
      },
      fontFamily: {
        sans: [
          'Inter',
          'ui-sans-serif',
          'system-ui',
          '-apple-system',
          'BlinkMacSystemFont',
          'Segoe UI',
          'Roboto',
          'Helvetica Neue',
          'Arial',
          'sans-serif',
        ],
        mono: [
          'JetBrains Mono',
          'ui-monospace',
          'SFMono-Regular',
          'Menlo',
          'Monaco',
          'Consolas',
          'Liberation Mono',
          'Courier New',
          'monospace',
        ],
      },
      transitionTimingFunction: {
        'out-strong': 'cubic-bezier(0.23, 1, 0.32, 1)',
        'in-out-strong': 'cubic-bezier(0.77, 0, 0.175, 1)',
      },
      boxShadow: {
        raised: '0 0 0 1px rgba(255,255,255,0.04) inset, 0 8px 24px -6px rgba(0,0,0,0.4)',
      },
      animation: {
        shimmer: 'shimmer 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'fade-up': 'fadeUp 250ms ease-out forwards',
        'progress-fill': 'progressFill 0.8s cubic-bezier(0.23, 1, 0.32, 1) forwards',
        'cursor-blink': 'cursorBlink 1s step-end infinite',
        'scan-sweep': 'scanSweep 2.5s ease-in-out infinite',
      },
      keyframes: {
        shimmer: {
          '0%, 100%': { opacity: '0.4' },
          '50%': { opacity: '0.8' },
        },
        fadeUp: {
          from: { opacity: '0', transform: 'translateY(8px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
        progressFill: {
          from: { width: '0%' },
          to: { width: '100%' },
        },
        cursorBlink: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0' },
        },
        scanSweep: {
          '0%': { transform: 'translateX(-100%)' },
          '100%': { transform: 'translateX(100%)' },
        },
      },
    },
  },
  plugins: [],
}

export default config
