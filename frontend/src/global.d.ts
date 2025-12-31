// Type declarations for static assets and styles
declare module '*.css';
declare module '*.scss';
declare module '*.sass';
declare module '*.less';
declare module '*.module.css';
declare module '*.module.scss';
declare module '*.module.sass';
declare module '*.png';
declare module '*.jpg';
declare module '*.jpeg';
declare module '*.gif';
declare module '*.svg';
declare module '*.webp';

interface ImportMetaEnv {
  readonly VITE_API_BASE?: string;
  // add more env vars here as needed
  readonly [key: string]: string | undefined;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
