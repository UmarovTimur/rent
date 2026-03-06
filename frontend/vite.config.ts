import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tsconfigPaths from 'vite-tsconfig-paths'

export default defineConfig({
    plugins: [react(), tsconfigPaths()],
    server: {
        host: '0.0.0.0',
        port: 5174,
        proxy: {
            '/api': {
                target: 'http://localhost:8000',
                changeOrigin: true,
            },
            '/media': {
                target: 'http://localhost:8000',
                changeOrigin: true,
            },
            '/admin': {
                target: 'http://localhost:8000',
                changeOrigin: true,
            },
        },
        allowedHosts: [
            'clustery-darell-uncopious.ngrok-free.dev'
        ]
    },
})
