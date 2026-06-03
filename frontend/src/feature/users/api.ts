import { queryOptions } from "@tanstack/react-query";

import { apiClient } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";

export type User = components["schemas"]["UserRead"];
export type Role = components["schemas"]["RoleRead"];
export type UserCreate = components["schemas"]["UserCreate"];
export type UserUpdate = components["schemas"]["UserUpdate"];

export const userKeys = {
  all: ["users"] as const,
  list: () => [...userKeys.all, "list"] as const,
};

export const roleKeys = {
  all: ["roles"] as const,
  list: () => [...roleKeys.all, "list"] as const,
};

// ---- backend を叩く関数（IO） ----

export async function fetchUsers(cookie?: string): Promise<User[]> {
  const { data, error } = await apiClient.GET("/api/v1/users/", {
    headers: cookie ? { Cookie: cookie } : undefined,
  });
  if (error) throw new Error("ユーザー一覧の取得に失敗しました");
  return data;
}

export async function fetchRoles(cookie?: string): Promise<Role[]> {
  const { data, error } = await apiClient.GET("/api/v1/roles/", {
    headers: cookie ? { Cookie: cookie } : undefined,
  });
  if (error) throw new Error("ロール一覧の取得に失敗しました");
  return data;
}

export async function createUser(body: UserCreate): Promise<User> {
  const { data, error } = await apiClient.POST("/api/v1/users/", { body });
  if (error) {
    // backend は重複ユーザー名などを detail（文字列）で返す
    throw new Error(
      typeof error.detail === "string" ? error.detail : "ユーザーの作成に失敗しました",
    );
  }
  return data;
}

export async function updateUser(id: number, body: UserUpdate): Promise<User> {
  const { data, error } = await apiClient.PATCH("/api/v1/users/{user_id}", {
    params: { path: { user_id: id } },
    body,
  });
  if (error) throw new Error("ユーザーの更新に失敗しました");
  return data;
}

export async function deleteUser(id: number): Promise<void> {
  const { error } = await apiClient.DELETE("/api/v1/users/{user_id}", {
    params: { path: { user_id: id } },
  });
  if (error) throw new Error("ユーザーの削除に失敗しました");
}

export function usersQueryOptions(cookie?: string) {
  return queryOptions({ queryKey: userKeys.list(), queryFn: () => fetchUsers(cookie) });
}

export function rolesQueryOptions(cookie?: string) {
  return queryOptions({ queryKey: roleKeys.list(), queryFn: () => fetchRoles(cookie) });
}
