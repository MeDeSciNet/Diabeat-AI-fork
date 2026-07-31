import { fileURLToPath, URL } from 'node:url';

import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      // Shared UI and the generated schema types are consumed through aliases
      // rather than published packages: one repo, one source of truth.
      '@shared': fileURLToPath(new URL('../web-shared/src', import.meta.url)),
      '@somno/types': fileURLToPath(
        new URL('../shared-schemas/generated/ts/somno-types.ts', import.meta.url),
      ),
    },
  },
  server: { host: '0.0.0.0', port: 5174 },
  preview: { host: '0.0.0.0', port: 5174 },
});
