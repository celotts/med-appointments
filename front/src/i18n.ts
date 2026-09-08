import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';

i18n.use(initReactI18next).init({
  resources: {
    en: {
      translation: {
        "welcome": "Welcome",
        "logout": "Logout",
        "dashboard": "Dashboard",
        "appointments": "Appointments",
        "patients": "Patients",
        "doctors": "Doctors",
        "ai_assistant": "AI Assistant",
        "reports": "Reports",
        "settings": "Settings",
        "login": "Login",
        "email": "Email",
        "password": "Password",
        "signIn": "Sign In",
      },
    },
    es: {
      translation: {
        "welcome": "Bienvenido",
        "logout": "Cerrar Sesión",
        "dashboard": "Panel Principal",
        "appointments": "Citas",
        "patients": "Pacientes",
        "doctors": "Médicos",
        "ai_assistant": "Asistente IA",
        "reports": "Reportes",
        "settings": "Configuración",
        "login": "Iniciar Sesión",
        "email": "Correo Electrónico",
        "password": "Contraseña",
        "signIn": "Entrar",
      },
    },
  },
  lng: 'es',
  fallbackLng: 'en',
  interpolation: {
    escapeValue: false,
  },
});

export default i18n;
