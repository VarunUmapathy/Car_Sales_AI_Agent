/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: "#004ac6",
        background: "#f7f9fb",
        surface: "#f7f9fb",
        "on-surface": "#191c1e",
        "on-surface-variant": "#434655",
        "outline-variant": "#c3c6d7",
        "primary-container": "#2563eb",
      },
      fontFamily: {
        body: ["Inter", "sans-serif"],
        headline: ["Hanken Grotesk", "sans-serif"],
      }
    },
  },
  plugins: [],
}