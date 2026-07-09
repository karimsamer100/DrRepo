import type { Config } from 'tailwindcss'

const config: Config = {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        base: '#0b0f17',
        surface: '#121826',
        'surface-2': '#1a2233',
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
        faint: '#64748b',
      },
      fontFamily: {
        sans: [
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
      animation: {
        shimmer: 'shimmer 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'fade-up': 'fadeUp 250ms ease-out forwards',
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
      },
    },
  },
  plugins: [],
}

export default config
