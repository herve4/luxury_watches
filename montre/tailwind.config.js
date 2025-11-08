/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./montre/templates/**/*.html",
    "./montre/static/src/**/*.js",
  ],
  theme: {
    extend: {
      fontFamily: {
        'playfair': ['Playfair Display', 'serif'],
        'inter': ['Inter', 'sans-serif'],
      },
      colors: {
        'amber': {
          400: '#fbbf24',
          500: '#f59e0b',
          600: '#d97706',
        },
        'slate': {
          300: '#cbd5e1',
          400: '#94a3b8',
          500: '#64748b',
          600: '#475569',
          700: '#334155',
          800: '#1e293b',
          900: '#0f172a',
        },
      },
    },
  },
  plugins: [],
}
