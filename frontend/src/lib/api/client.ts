import createClient from "openapi-fetch";
import type { paths } from "./schema";
import { env } from "@/lib/env";

/**
 * API クライアントのベース URL を解決する。
 *
 * - サーバー側 (Server Component) では、コンテナ間通信を使う必要があるので INTERNAL_API_URL を使う。
 * - クライアント側 (ブラウザで実行される Client Component) では、ホスト OS から見える NEXT_PUBLIC_API_URL を使う。
 */
function resolveBaseUrl(): string {
  // Server / Client で fetch する宛先 が異なるので、 window の存在で現在の実行場所を判定する。
  // - windowが存在=ブラウザ側
  // - windowが存在しない=サーバー側
  return typeof window === "undefined"
    ? env.INTERNAL_API_URL
    : env.NEXT_PUBLIC_API_URL;
}

// createClient に schema.ts の paths 型を渡すと、 第1引数は backend が公開しているパス文字列のユニオン型に限定され、 body / params もパスに対応する型に自動で絞られる
export const apiClient = createClient<paths>({
  baseUrl: resolveBaseUrl(),
  // fetch のデフォルトは "same-origin" (Cookie を同一オリジン以外に送らない)。
  // frontend(:3000) -> backend(:8000) のアクセスはクロスオリジン扱いなので Cookieを送信するには "include" 必須。
  // backend 側の CORS で allow_credentials=True が設定されているのと対になる。
  credentials: "include",
});