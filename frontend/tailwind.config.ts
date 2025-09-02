import type { Config } from 'tailwindcss';

const config: Config = {
  darkMode: ['class'],
  content: [
    './pages/**/*.{ts,tsx}',
    './components/**/*.{ts,tsx}',
    './app/**/*.{ts,tsx}',
    './src/**/*.{ts,tsx}',
  ],
  theme: {
    container: {
      center: true,
      padding: '2rem',
      screens: {
        '2xl': '1400px',
      },
    },
    extend: {
      colors: {
        primary: '#2563eb',
        accent: '#10b981',
        muted: '#f8fafc',
        border: '#e5e7eb',
      },
      boxShadow: {
        soft: '0 2px 6px rgba(0,0,0,0.05)',
      },
      borderRadius: {
        DEFAULT: '1rem',
        '2xl': '1rem',
      },
    },
  },
  plugins: [require('tailwindcss-animate')],
};

export default config;
