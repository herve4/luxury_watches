module.exports = {
  content: [
    './templates/**/*.html',
    './static/js/**/*.js',
  ],
  theme: {
    extend: {
      colors: {
        'gold': {
          500: '#D4AF37',
        },
        'black': '#000000',
      },
      fontFamily: {
        'playfair': ['Playfair Display', 'serif'],
        'inter': ['Inter', 'sans-serif'],
      },
      animation: {
        'fade-in': 'fadeIn 0.8s ease-in-out',
        'slide-up': 'slideUp 0.6s ease-out',
      }
    },
  },
  plugins: [],
}