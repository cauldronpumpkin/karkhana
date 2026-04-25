import { defineConfig } from 'vitest/config'
import { svelte } from '@sveltejs/vite-plugin-svelte'
import path from 'path'

// https://vite.dev/config/
export default defineConfig({
  plugins: [svelte({
    compilerOptions: {
      css: 'injected',
    },
  })],
  server: {
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        ws: true,
      },
    },
  },
  resolve: {
    alias: [
      {
        find: '$app/stores',
        replacement: path.resolve(__dirname, 'src/mocks/app-stores.svelte.js'),
      },
      {
        find: '$app/navigation',
        replacement: path.resolve(__dirname, 'src/mocks/app-navigation.js'),
      },
    ],
    conditions: ['browser'],
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test-setup.js'],
  },
})
