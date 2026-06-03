import { cookies } from "next/headers";
import { dehydrate, HydrationBoundary } from "@tanstack/react-query";
import type { Metadata } from "next";

import { getQueryClient } from "@/lib/query/get-query-client";
import { itemsQueryOptions } from "@/feature/items/api";

import { ItemsView } from "./items-view";

export const metadata: Metadata = {
  title: "アイテム管理 | Web Tutorial v2",
};

export default async function ItemsPage() {
  // Next.js 16 では cookies() は非同期。await が必要
  const cookie = (await cookies()).toString();
  const queryClient = getQueryClient();

  // サーバー側で一覧を取得してキャッシュに載せる
  await queryClient.prefetchQuery(itemsQueryOptions(cookie));

  return (
    // dehydrate でキャッシュを直列化し、HydrationBoundary 経由でクライアントへ渡す
    <HydrationBoundary state={dehydrate(queryClient)}>
      <ItemsView />
    </HydrationBoundary>
  );
}
