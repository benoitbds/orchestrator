import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  eslint: { ignoreDuringBuilds: true },   // déjà présent
  output: "standalone",                   // ← ajoute ceci
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "http://192.168.1.93:8000/:path*",
      },
    ];
  },
};

export default nextConfig;
