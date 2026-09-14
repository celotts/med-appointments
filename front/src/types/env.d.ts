// Type declarations for import.meta.env
declare global {
  interface ImportMeta {
    env: {
      VITE_API_BASE_URL: string;
    };
  }
}
