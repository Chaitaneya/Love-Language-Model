import { defineConfig } from "vite";

// Production CSP: same-origin only. 'wasm-unsafe-eval' lets WebAssembly (Pyodide) compile; nothing else.
// No inline styles or scripts: the UI sets styles through the CSSOM, which style-src allows.
const CSP = [
  "default-src 'none'",
  "script-src 'self' 'wasm-unsafe-eval'",
  "worker-src 'self'",
  "connect-src 'self'",
  "style-src 'self'",
  "img-src 'self' data: blob:",
  "font-src 'self'",
  "base-uri 'none'",
  "form-action 'none'",
  "object-src 'none'",
].join("; ");

// For hosts that read a `_headers` file (Cloudflare Pages, Netlify). It adds what a <meta> tag cannot do:
// frame-ancestors, and the other standard hardening headers. GitHub Pages ignores the file; the <meta> CSP still applies there.
const HEADERS = `/*
  Content-Security-Policy: ${CSP}; frame-ancestors 'none'
  X-Content-Type-Options: nosniff
  Referrer-Policy: no-referrer
  Permissions-Policy: camera=(), microphone=(), geolocation=(), payment=(), usb=(), interest-cohort=()
  Cross-Origin-Opener-Policy: same-origin
  Cross-Origin-Resource-Policy: same-origin

/assets/*
  Cache-Control: public, max-age=31536000, immutable
`;

export default defineConfig({
  base: "./", // relative, so the site works from a sub-path such as github.io/<repo>/
  build: { target: "es2022", sourcemap: false },
  worker: { format: "iife" },
  server: { port: 5173, strictPort: true },
  preview: { port: 4173, strictPort: true },
  plugins: [
    {
      name: "csp-in-production",
      apply: "build",
      transformIndexHtml: (html) =>
        html.replace("<!--CSP-->", `<meta http-equiv="Content-Security-Policy" content="${CSP}">`),
      generateBundle() { this.emitFile({ type: "asset", fileName: "_headers", source: HEADERS }); },
    },
  ],
});
