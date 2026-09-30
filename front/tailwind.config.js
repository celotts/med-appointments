/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Paleta medica. Los 4 colores base son los unicos estables:
        //   primary   #2C5AA0  consultas
        //   operation #D22B2B  operaciones
        //   visit     #F57C00  visitas post-operatorio
        //   personal  #2E7D32  actividades personales
        medical: {
          primary: '#2C5AA0',
          operation: '#D22B2B',
          visit: '#F57C00',
          personal: '#2E7D32',

          // Alias semanticos. El codigo existente usa `secondary`, `danger`,
          // `success` y `warning` en 68 sitios; antes esas claves NO existian
          // en el theme, asi que Tailwind no emitia las clases y todos esos
          // estilos se perdian en silencio. Se definen para que apliquen.
          secondary: '#2C5AA0', // alias de primary (anillo de foco)
          danger: '#D22B2B',
          success: '#2E7D32',
          warning: '#F57C00',

          // Variantes oscuras, conservadas de la config anterior.
          primaryDark: '#1E3A5F',
          secondaryDark: '#A8201F',
          warningDark: '#C05A0E',
          successDark: '#1A4A2E',
        },
      },
      // `medicalText.main` genera `text-medicalText-main`, pero el codigo usa
      // `text-medical-textMain` (y `bg-medical-background`). Esas claves no
      // existian, asi que Tailwind no emitia las clases y 130+ estilos se
      // perdian en silencio. Se redefinen con el nombre que el codigo usa.
      textColor: {
        'medical-textMain': '#1E293B',
        'medical-textMuted': '#64748B',
      },
      backgroundColor: {
        'medical-background': '#F8FAFC',
      },
      ringColor: {
        'medical-secondary': '#2C5AA0',
      },
      borderColor: {
        'medical-textMuted': '#64748B',
      },
    },
  },
  plugins: [],
}