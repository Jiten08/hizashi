// The owner's phone app: a PWA served by the hub at /app/ (the dashboard lives at /).
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";
import { VitePWA } from "vite-plugin-pwa";

const HUB = "http://127.0.0.1:8000";

export default defineConfig({
  base: "/app/",
  plugins: [
    react(),
    tailwindcss(),
    VitePWA({
      registerType: "autoUpdate",
      includeAssets: ["icon.svg", "apple-touch-icon.png"],
      manifest: {
        name: "Hizashi",
        short_name: "Hizashi",
        description: "Your home's energy agent: sells spare rooftop power to neighbours, inside limits you set.",
        id: "/app/",
        start_url: "/app/",
        scope: "/app/",
        display: "standalone",
        orientation: "portrait",
        theme_color: "#f2f2f7",
        background_color: "#f2f2f7",
        icons: [
          { src: "icon-192.png", sizes: "192x192", type: "image/png" },
          { src: "icon-512.png", sizes: "512x512", type: "image/png" },
          { src: "icon-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
        ],
      },
      workbox: {
        navigateFallback: "/app/index.html",
        navigateFallbackAllowlist: [/^\/app\//],
        navigateFallbackDenylist: [/^\/api/, /^\/ws/],
      },
    }),
  ],
  server: {
    host: true,
    port: 5174,
    proxy: { "/api": HUB, "/ws": { target: HUB, ws: true } },
  },
});
