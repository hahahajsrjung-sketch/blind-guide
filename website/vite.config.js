import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// 뼈대 단계: 페이지가 뜨고 폼이 백엔드로 값을 보내는 데 집중한다.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
  },
})
