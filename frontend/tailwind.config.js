/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        gold: {
          DEFAULT: "#C9A84C",
          light: "#D4AF6A",
          dark: "#A8882E",
          muted: "rgba(201,168,76,0.15)",
        },
        navy: {
          DEFAULT: "#0D1B2A",
          light: "#1A2B3C",
          card: "#111827",
          border: "rgba(255,255,255,0.08)",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
      },
      borderColor: {
        subtle: "rgba(255,255,255,0.08)",
      },
    },
  },
  plugins: [],
}
