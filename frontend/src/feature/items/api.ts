import { queryOptions } from "@tanstack/react-query";

import { apiClient } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";

// schema.ts から型を借りる（backend の型と常に一致する）
export type Item = components["schemas"]["ItemRead"];
export type ItemInput = components["schemas"]["ItemCreate"]; // { title, content }

// queryKey を 1 か所に集約。誤字や不一致を防ぐ
export const itemKeys = {
  all: ["items"] as const,
  list: () => [...itemKeys.all, "list"] as const,
};

// ---- backend を叩く関数（IO） ----

/**
 * アイテム一覧を取得する。
 * - サーバー実行時 (prefetch): cookie を引数で受け取りヘッダに載せる
 * - クライアント実行時: cookie は undefined。apiClient が credentials:"include" で自動送信する
 */
export async function fetchItems(cookie?: string): Promise<Item[]> {
  const { data, error } = await apiClient.GET("/api/v1/items/", {
    headers: cookie ? { Cookie: cookie } : undefined,
  });
  if (error) throw new Error("アイテム一覧の取得に失敗しました");
  return data;
}

export async function createItem(input: ItemInput): Promise<Item> {
  const { data, error } = await apiClient.POST("/api/v1/items/", { body: input });
  if (error) throw new Error("アイテムの作成に失敗しました");
  return data;
}

export async function updateItem(id: number, input: ItemInput): Promise<Item> {
  const { data, error } = await apiClient.PATCH("/api/v1/items/{item_id}", {
    params: { path: { item_id: id } },
    body: input,
  });
  if (error) throw new Error("アイテムの更新に失敗しました");
  return data;
}

export async function deleteItem(id: number): Promise<void> {
  const { error } = await apiClient.DELETE("/api/v1/items/{item_id}", {
    params: { path: { item_id: id } },
  });
  if (error) throw new Error("アイテムの削除に失敗しました");
}

// server / client 双方から使う queryOptions（queryKey を共有しつつ Cookie の渡し方を吸収）
export function itemsQueryOptions(cookie?: string) {
  return queryOptions({
    queryKey: itemKeys.list(),
    queryFn: () => fetchItems(cookie),
  });
}