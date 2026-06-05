import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  reactCompiler: true,
  // proxy, localhost オリジンに開発用リソース（`/_next/*` や HMR）へのアクセスを許可する
  allowedDevOrigins: ["proxy", "localhost"],
  // 本番ビルドで .next/standalone（自己完結サーバー）を出力する
  output: "standalone",
};

export default nextConfig;
