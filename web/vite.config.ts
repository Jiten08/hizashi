import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { VitePWA } from "vite-plugin-pwa";

const HUB = "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    VitePWA({
      registerType: "autoUpdate",
      includeAssets: ["sun.svg"],
      manifest: {
        name: "Hizashi",
        short_name: "Hizashi",
        description: "Your home's solar agent: sells spare power to neighbours, inside your limits.",
        theme_color: "#d98a04",
        background_color: "#fffaf0",
        display: "standalone",
        start_url: "/",
        icons: [{ src: "sun.svg", sizes: "any", type: "image/svg+xml", purpose: "any maskable" }],
      },
      workbox: {
        navigateFallbackDenylist: [/^\/api/, /^\/ws/, /^\/webhooks/],
      },
    }),
  ],
  server: {
    host: true,
    proxy: {
      "/api": HUB,
      "/ws": { target: HUB, ws: true },
    },
  },
});
