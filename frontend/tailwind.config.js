/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: ["class"],
  content: [
    './pages/**/*.{ts,tsx}',
    './components/**/*.{ts,tsx}',
    './app/**/*.{ts,tsx}',
    './src/**/*.{ts,tsx}',
  ],
  prefix: "",
  theme: {
    container: {
      center: true,
      padding: "2rem",
      screens: {
        "2xl": "1400px",
      },
    },
    extend: {
      keyframes: {
        "glow": {
          '0%': { boxShadow: '0 0 10px rgba(34, 197, 94, 0.8)', backgroundColor: 'rgba(34, 197, 94, 0.1)' },
          '100%': { boxShadow: 'none', backgroundColor: 'transparent' },
        },
      },
      animation: {
        "glow": "glow 1.5s ease-out",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
}