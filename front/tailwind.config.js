/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        medical: {
          primary: '#1E3A8A',   // blue-900
          secondary: '#3B82F6', // blue-500
          accent: '#10B981',    // emerald-500
          background: '#F8FAFC', // slate-50
          surface: '#FFFFFF',
          textMain: '#1E293B',   // slate-800
          textMuted: '#64748B',   // slate-500
        },
      },
    },
  },
  plugins: [],
}
