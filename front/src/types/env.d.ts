// Type declarations for import.meta.env
declare global {
  interface ImportMeta {
    env: {
      VITE_API_BASE_URL: string;
    };
  }
}

declare module '*.css';
declare module '*.svg';
declare module '*.png';
