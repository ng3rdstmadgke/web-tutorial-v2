import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  reactCompiler: true,
  // proxy, localhost オリジンに開発用リソース（`/_next/*` や HMR）へのアクセスを許可する
  allowedDevOrigins: ["proxy", "localhost"],
};

export default nextConfig;
