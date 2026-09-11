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
          primary: '#2C5AA0',     // consultas
          operation: '#D22B2B',   // operaciones
          visit: '#F57C00',       // visitas post-operatorio
          personal: '#2E7D32',    // actividades personales/vacaciones
          primaryDark: '#1E3A5F',
          secondaryDark: '#A8201F',
          warningDark: '#C05A0E',
          successDark: '#1A4A2E',
        },
        medicalText: {
          main: '#1E293B',
          muted: '#64748B',
        },
        medicalBackground: {
          page: '#F8FAFC',
        },
      },
    },
  },
  plugins: [],
}
