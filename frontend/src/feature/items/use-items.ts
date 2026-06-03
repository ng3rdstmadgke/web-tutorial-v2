import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import {
  itemKeys,
  itemsQueryOptions,
  createItem,
  updateItem,
  deleteItem,
  type Item,
  type ItemInput,
} from "./api";

// 一覧取得（prefetch 済みのキャッシュをそのまま使う）
export function useItems() {
  return useQuery(itemsQueryOptions());
}

// 作成・編集。mode で呼ぶ API を切り替え、成功したら一覧を再取得する
export function useSaveItem(args: {
  mode: "create" | "edit";
  itemId?: number;
  onSuccess?: () => void;
}) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (input: ItemInput) =>
      args.mode === "create" ? createItem(input) : updateItem(args.itemId!, input),
    onSuccess: () => {
      // 一覧キャッシュを無効化 -> useItems が自動で再取得
      queryClient.invalidateQueries({ queryKey: itemKeys.list() });
      toast.success(args.mode === "create" ? "アイテムを作成しました" : "アイテムを更新しました");
      args.onSuccess?.();
    },
  });
}

// 削除（楽観的更新: 応答を待たず一覧から消し、失敗したら戻す）
export function useDeleteItem() {
  const queryClient = useQueryClient();
  const listKey = itemKeys.list();

  return useMutation({
    mutationFn: deleteItem,

    // mutate(id) が呼ばれた直後（サーバー応答前）に実行される
    onMutate: async (id: number) => {
      // 進行中の再フェッチを止める（楽観的更新を上書きされないように）
      await queryClient.cancelQueries({ queryKey: listKey });
      // ロールバック用に現在のキャッシュを退避
      const previous = queryClient.getQueryData<Item[]>(listKey);
      // キャッシュから対象を除去 -> 一覧から即座に消える
      queryClient.setQueryData<Item[]>(listKey, (old) =>
        (old ?? []).filter((it) => it.id !== id),
      );
      // 戻り値は onError / onSettled の第 3 引数として受け取れる
      return { previous };
    },

    // 失敗したら、退避しておいたキャッシュで元に戻す
    onError: (_err, _id, ctx) => {
      if (ctx?.previous) queryClient.setQueryData(listKey, ctx.previous);
      toast.error("削除に失敗しました");
    },

    onSuccess: () => toast.success("アイテムを削除しました"),

    // 成功・失敗のどちらでも、最後にサーバーと再同期する
    onSettled: () => queryClient.invalidateQueries({ queryKey: listKey }),
  });
}