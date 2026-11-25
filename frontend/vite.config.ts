/// <reference types="vitest/config" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// ADR 0005: the browser only ever talks to ONE address (localhost:5173).
// Anything under /api is quietly forwarded to FastAPI on port 8000, so the
// sign-in cookie belongs to this address and is sent with every API call.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: true, // QR codes and Google expect 5173 exactly
    proxy: {
      // changeOrigin stays false: FastAPI then sees "localhost:5173" as the host,
      // so it tells Google to send people back HERE after sign-in.
      "/api": { target: "http://127.0.0.1:8000", changeOrigin: false },
    },
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test-setup.ts"],
  },
});
