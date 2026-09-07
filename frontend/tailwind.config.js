/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        irr: {
          bg: 'oklch(0.16 0.02 250)',
          panel: 'oklch(0.205 0.018 250)',
          'panel-alt': 'oklch(0.24 0.02 250)',
          border: 'oklch(0.32 0.025 250)',
          'border-strong': 'oklch(0.42 0.03 250)',
          text: 'oklch(0.93 0.008 250)',
          muted: 'oklch(0.64 0.018 250)',
          dim: 'oklch(0.47 0.018 250)',
          accent: 'oklch(0.78 0.135 200)',
          'accent-dim': 'oklch(0.30 0.05 200)',
          amber: 'oklch(0.78 0.135 70)',
          'amber-dim': 'oklch(0.32 0.055 70)',
          violet: 'oklch(0.74 0.115 300)',
          'violet-dim': 'oklch(0.30 0.05 300)',
          green: 'oklch(0.72 0.135 145)',
          'green-dim': 'oklch(0.30 0.05 145)',
        },
      },
      fontFamily: {
        display: ['Rajdhani', 'Arial Narrow', 'sans-serif'],
        mono: ['IBM Plex Mono', 'Consolas', 'SFMono-Regular', 'monospace'],
      },
    },
  },
  plugins: [],
}
