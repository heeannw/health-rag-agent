import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  // .env는 저장소 루트 하나로 관리한다 (VITE_ 접두사 키만 브라우저에 노출됨)
  envDir: '../..',
  server: {
    // /api 요청은 FastAPI(agent/backend)로 넘긴다
    proxy: { '/api': 'http://localhost:8000' },
  },
})
