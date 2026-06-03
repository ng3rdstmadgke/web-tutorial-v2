"use client";

import { QueryClientProvider } from "@tanstack/react-query";

import { getQueryClient } from "@/lib/query/get-query-client";

export function Providers({ children }: { children: React.ReactNode }) {
  // getQueryClient はブラウザではシングルトンを返すので useState で固定する必要はない
  const queryClient = getQueryClient();

  return (
    // children のツリー全体で queryClient を参照できるになる
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}