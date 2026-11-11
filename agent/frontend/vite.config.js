import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  // 루트 .env 사용 (VITE_ 키만 브라우저에 노출)
  envDir: '../..',
  server: {
    // /api → FastAPI
    proxy: { '/api': 'http://localhost:8000' },
  },
})
