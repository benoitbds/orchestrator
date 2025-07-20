import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  eslint: { ignoreDuringBuilds: true },   // déjà présent
  output: "standalone",                   // ← ajoute ceci
};

export default nextConfig;
