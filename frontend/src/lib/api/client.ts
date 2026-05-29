import createClient from "openapi-fetch";
import type { paths } from "./schema";
import { env } from "@/lib/env";

/**
 * API クライアントのベース URL を解決する。
 *
 * - サーバー側 (Server Component): コンテナ間通信で backend に直接アクセスするので INTERNAL_API_URL を使う。
 * - クライアント側 (ブラウザ): nginx リバースプロキシ経由の同一オリジンで `/api/...` を叩くので、ベース URL は空 (相対) にする。
 */
function resolveBaseUrl(): string {
  // window の有無で実行場所を判定 (window あり=ブラウザ / window なし=サーバー)
  return typeof window === "undefined" ? env.INTERNAL_API_URL : "";
}

// createClient に schema.ts の paths 型を渡すと、 第1引数は backend が公開しているパス文字列のユニオン型に限定され、 body / params もパスに対応する型に自動で絞られる
export const apiClient = createClient<paths>({
  baseUrl: resolveBaseUrl(),
  // 同一オリジン (nginx 経由) なので Cookie は自動送信されるが、明示しておく
  credentials: "include",
});