import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import {
  userKeys,
  usersQueryOptions,
  rolesQueryOptions,
  createUser,
  updateUser,
  deleteUser,
  type User,
} from "./api";

// フォームの入力値（作成・編集で共通の形）
export type UserFormValues = {
  username: string;
  password: string;
  role_ids: number[];
};

export function useUsers() {
  return useQuery(usersQueryOptions());
}

export function useRoles() {
  return useQuery(rolesQueryOptions());
}

// 作成・編集。mode でリクエストの形を組み立て分ける
export function useSaveUser(args: {
  mode: "create" | "edit";
  userId?: number;
  onSuccess?: () => void;
}) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (values: UserFormValues) => {
      if (args.mode === "create") {
        return createUser({
          username: values.username,
          password: values.password,
          role_ids: values.role_ids,
        });
      }
      // 編集: username は変更不可。password は入力があるときだけ送る
      return updateUser(args.userId!, {
        role_ids: values.role_ids,
        ...(values.password ? { password: values.password } : {}),
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: userKeys.list() });
      toast.success(args.mode === "create" ? "ユーザーを作成しました" : "ユーザーを更新しました");
      args.onSuccess?.();
    },
  });
}

// 削除（items と同じ楽観的更新パターン）
export function useDeleteUser() {
  const queryClient = useQueryClient();
  const listKey = userKeys.list();

  return useMutation({
    mutationFn: deleteUser,
    onMutate: async (id: number) => {
      await queryClient.cancelQueries({ queryKey: listKey });
      const previous = queryClient.getQueryData<User[]>(listKey);
      queryClient.setQueryData<User[]>(listKey, (old) =>
        (old ?? []).filter((u) => u.id !== id),
      );
      return { previous };
    },
    onError: (_err, _id, ctx) => {
      if (ctx?.previous) queryClient.setQueryData(listKey, ctx.previous);
      toast.error("削除に失敗しました");
    },
    onSuccess: () => toast.success("ユーザーを削除しました"),
    onSettled: () => queryClient.invalidateQueries({ queryKey: listKey }),
  });
}
