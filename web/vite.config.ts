import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The vault API and this UI are served from the same origin in production
// (see ../README.md); in dev, proxy /api and /v2 to a locally running
// uvicorn instance so the browser never needs CORS at all during development.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": "https://localhost:2053",
      "/v2": "https://localhost:2053",
    },
  },
  build: {
    outDir: "dist",
    sourcemap: true,
  },
});
