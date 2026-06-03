import { QueryClient, environmentManager } from "@tanstack/react-query";

function makeQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        // staleTime: 取得データを「新鮮 (fresh)」とみなす時間。
        // fresh の間は再マウント・タブの再フォーカス・再接続時の自動再取得を抑える。
        // 期限切れ (stale) になっても自動では API を叩かず、次のトリガー時に取り直すだけ。
        // 60 秒に設定し、prefetch 直後にブラウザで即再取得が走るのを防ぐ。
        staleTime: 60 * 1000,
      },
    },
  });
}

let browserQueryClient: QueryClient | undefined = undefined;

export function getQueryClient() {
  // サーバー実行かどうかを判定する
  if (environmentManager.isServer()) {
    // サーバー: 毎回新しいインスタンス
    return makeQueryClient();
  }
  // ブラウザ: シングルトン
  if (!browserQueryClient) browserQueryClient = makeQueryClient();
  return browserQueryClient;
}