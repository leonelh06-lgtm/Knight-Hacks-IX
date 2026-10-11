import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
export default defineConfig({
  plugins: [react()],
  base: "/play/",
  build: { outDir: "../game/fight/play", emptyOutDir: true },
  server: {
    proxy: Object.fromEntries(
      [
        "/debug.html",
        "/tracking",
        "/assets",
        "/maps",
        "/intro.css",
        "^/(?!play/|src/|node_modules/|@).*\\.(mjs|js)$",
      ].map((path) => [path, { target: "http://127.0.0.1:8000" }]),
    ),
  },
  test: { environment: "jsdom", setupFiles: ["./src/test-setup.js"] },
});
