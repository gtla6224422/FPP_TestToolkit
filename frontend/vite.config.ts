import { fileURLToPath, URL } from "node:url";
import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  server: {
    host: "0.0.0.0",
    port: 5173,
    proxy: {
      "/api-local": {
        target: "http://127.0.0.1:5003",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api-local/, ""),
      },
      "/api-cloud": {
        target: "http://8.134.195.209:5003",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api-cloud/, ""),
      },
    },
  },
});
