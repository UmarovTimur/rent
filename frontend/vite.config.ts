import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tsconfigPaths from 'vite-tsconfig-paths'

// Inside Docker the backend is reachable via its service name.
// Outside Docker (plain `npm run dev`) it's on localhost.
const backendTarget = process.env.BACKEND_INTERNAL_URL ?? 'http://localhost:8000'

export default defineConfig({
    plugins: [react(), tsconfigPaths()],
    server: {
        host: '0.0.0.0',
        port: 5174,
        proxy: {
            '/api': {
                target: backendTarget,
                changeOrigin: true,
            },
            '/media': {
                target: backendTarget,
                changeOrigin: true,
            },
            '/admin': {
                target: backendTarget,
                changeOrigin: true,
            },
        },
        allowedHosts: [
            'clustery-darell-uncopious.ngrok-free.dev'
        ]
    },
})
