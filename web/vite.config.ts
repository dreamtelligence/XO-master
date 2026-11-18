import { defineConfig } from 'vite'

export default defineConfig({
  server: {
    host: '127.0.0.1',
    port: 5173,
    strictPort: true,
    proxy: { '/api/fx-live': { target: 'ws://127.0.0.1:8765', ws: true }, '/api': { target: 'http://127.0.0.1:8765' } },
  },
})
