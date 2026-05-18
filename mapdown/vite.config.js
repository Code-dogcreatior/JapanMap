import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import cesium from 'vite-plugin-cesium'

export default defineConfig({
  plugins: [vue(), cesium()],
  server: {
    proxy: {
      '/api': 'http://localhost:5000',
      '/map_tiles_3d': 'http://localhost:5000',
      '/map_tiles': 'http://localhost:5000',
      '/plateau_tiles': 'http://localhost:5000',
      '/plateau-api': {
        target: 'https://api.plateauview.mlit.go.jp',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/plateau-api/, ''),
      },
      '/gsi-dem-local': 'http://localhost:5000',
      '/gsi-dem': 'http://localhost:5000',
    }
  }
})
