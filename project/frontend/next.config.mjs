import { fileURLToPath } from "node:url";

/** @type {import('next').NextConfig} */
const nextConfig = {
  distDir: process.env.TSUKIMI_BUILD_DIR || ".next",
  turbopack: { root: fileURLToPath(new URL("..", import.meta.url)) },
  images: { unoptimized: true, remotePatterns: [{ protocol: "https", hostname: "lain.bgm.tv" }] },
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${process.env.TSUKIMI_API_ORIGIN || "http://127.0.0.1:8000"}/api/:path*` }];
  },
};

export default nextConfig;
