import { createEnv } from "@t3-oss/env-nextjs";
import { z } from "zod";

// createEnv: @t3-oss/env-nextjs の Next.js 用ヘルパー
// 欠損や型違反があれば起動時に Invalid environment variables: { ... } で落ちる
export const env = createEnv({
  /**
   * サーバー側でのみ使う変数。Server Component / Route Handler / proxy から参照する。
   * NEXT_PUBLIC_ で始まる名前を書こうとすると型レベルでエラーになる。
   */
  server: {
    // z.url(): URL 形式の文字列であることを検証
    INTERNAL_API_URL: z.url(),
  },

  /**
   * クライアントに公開する変数。
   * クライアント側 API は nginx 経由の同一オリジン(相対 /api)で叩くため、ベース URL の環境変数は不要。
   */
  client: {},

  /**
   * 実際の値を渡す。
   */
  runtimeEnv: {
    INTERNAL_API_URL: process.env.INTERNAL_API_URL,
  },
});