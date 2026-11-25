/// <reference types="vitest/config" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { VitePWA } from "vite-plugin-pwa";

// ADR 0005: the browser only ever talks to ONE address (localhost:5173).
// Anything under /api is quietly forwarded to FastAPI on port 8000, so the
// sign-in cookie belongs to this address and is sent with every API call.
export default defineConfig({
  plugins: [
    react(),
    // Makes the app installable ("Add to Home Screen") and able to open with no signal.
    VitePWA({
      registerType: "autoUpdate", // a new deploy replaces the old app on the next visit
      includeAssets: ["favicon.png", "apple-touch-icon.png"],
      manifest: {
        name: "Event Companion",
        short_name: "Companion",
        description: "Your conference in your pocket: agenda, booth visits and leads.",
        theme_color: "#15191C",
        background_color: "#15191C",
        display: "standalone",
        start_url: "/",
        icons: [
          { src: "icon-192.png", sizes: "192x192", type: "image/png" },
          { src: "icon-512.png", sizes: "512x512", type: "image/png" },
          { src: "icon-maskable-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
        ],
      },
      workbox: {
        // The app itself (HTML, JS, CSS, icons) is saved on the phone at install.
        globPatterns: ["**/*.{js,css,html,png,svg}"],
        // Any app page (/scan/abc, /agenda...) opens offline from the saved index.html,
        // but /api requests must ALWAYS go to the real server.
        navigateFallback: "/index.html",
        navigateFallbackDenylist: [/^\/api\//],
        // 🧠 What we save from the API, and what we never save:
        //  - the public agenda: yes. Network first, so it's fresh when there's signal,
        //    and the last copy still opens in a basement room with no Wi-Fi.
        //  - anything personal (sign-in, leads, visits) or any POST: no. Phones get
        //    shared and borrowed; private data shouldn't sit in a cache.
        runtimeCaching: [
          {
            urlPattern: ({ url, request }) =>
              request.method === "GET" && /^\/api\/events\/[^/]+\/agenda$/.test(url.pathname),
            handler: "NetworkFirst",
            options: {
              cacheName: "agenda",
              networkTimeoutSeconds: 4,
              expiration: { maxEntries: 5, maxAgeSeconds: 14 * 24 * 60 * 60 },
            },
          },
          {
            urlPattern: ({ url }) => url.origin === "https://fonts.googleapis.com" || url.origin === "https://fonts.gstatic.com",
            handler: "StaleWhileRevalidate",
            options: { cacheName: "fonts", expiration: { maxEntries: 20 } },
          },
        ],
      },
    }),
  ],
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
