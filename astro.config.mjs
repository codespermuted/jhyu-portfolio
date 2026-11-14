import { defineConfig } from 'astro/config';

export default defineConfig({
  site: process.env.SITE_URL || 'https://jhyu-portfolio.netlify.app',
  base: process.env.BASE_PATH || '/',
  output: 'static',
  trailingSlash: 'always',
  devToolbar: { enabled: false },
});
