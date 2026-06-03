import { cookies } from "next/headers";
import { dehydrate, HydrationBoundary } from "@tanstack/react-query";
import type { Metadata } from "next";

import { getQueryClient } from "@/lib/query/get-query-client";
import { usersQueryOptions, rolesQueryOptions } from "@/feature/users/api";

import { UsersView } from "./users-view";

export const metadata: Metadata = {
  title: "ユーザー管理 | Web Tutorial v2",
};

export default async function UsersPage() {
  const cookie = (await cookies()).toString();
  const queryClient = getQueryClient();

  // ユーザー一覧とロール一覧を並行で prefetch
  await Promise.all([
    queryClient.prefetchQuery(usersQueryOptions(cookie)),
    queryClient.prefetchQuery(rolesQueryOptions(cookie)),
  ]);

  return (
    <HydrationBoundary state={dehydrate(queryClient)}>
      <UsersView />
    </HydrationBoundary>
  );
}