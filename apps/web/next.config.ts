import type { NextConfig } from "next";

// In production Vercel Services sends /api/v1/* to the Python engine before
// Next.js sees it. Locally, `next dev` forwards it to the engine on :8000.
const engine = process.env.ENGINE_DEV_URL ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  async rewrites() {
    if (process.env.NODE_ENV !== "development") return [];
    return [{ source: "/api/v1/:path*", destination: `${engine}/api/v1/:path*` }];
  },
};

export default nextConfig;
