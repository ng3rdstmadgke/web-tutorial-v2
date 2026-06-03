"use client";

import { useState } from "react";
import { Pencil, Plus, Trash2 } from "lucide-react";

import { useItems } from "@/feature/items/use-items";
import type { Item } from "@/feature/items/api";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

import { ItemFormDialog } from "./item-form-dialog";
import { DeleteItemDialog } from "./delete-item-dialog";

export function ItemsView() {
  // prefetch 済みなので初回はキャッシュから即座に返る（staleTime 経過後に裏で再取得）
  const { data: items, error } = useItems();

  const [createOpen, setCreateOpen] = useState(false);
  // 編集・削除の対象（null = Dialog を閉じている）
  const [editing, setEditing] = useState<Item | null>(null);
  const [deleting, setDeleting] = useState<Item | null>(null);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">アイテム管理</h1>
        <Button onClick={() => setCreateOpen(true)}>
          <Plus />
          新規作成
        </Button>
      </div>

      {error && (
        <p className="text-sm text-red-600" role="alert">
          {error.message}
        </p>
      )}

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-16">ID</TableHead>
            <TableHead>タイトル</TableHead>
            <TableHead>内容</TableHead>
            <TableHead className="w-32 text-right">操作</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {items?.length === 0 && (
            <TableRow>
              <TableCell colSpan={4} className="text-center text-muted-foreground">
                アイテムがありません
              </TableCell>
            </TableRow>
          )}
          {items?.map((item) => (
            <TableRow key={item.id}>
              <TableCell>{item.id}</TableCell>
              <TableCell>{item.title}</TableCell>
              <TableCell>{item.content}</TableCell>
              <TableCell className="space-x-2 text-right">
                <Button
                  variant="outline"
                  size="icon"
                  aria-label="編集"
                  onClick={() => setEditing(item)}
                >
                  <Pencil />
                </Button>
                <Button
                  variant="destructive"
                  size="icon"
                  aria-label="削除"
                  onClick={() => setDeleting(item)}
                >
                  <Trash2 />
                </Button>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>

      {/* 作成 Dialog */}
      <ItemFormDialog mode="create" open={createOpen} onOpenChange={setCreateOpen} />

      {/* 編集 Dialog（editing が null でなければ開く） */}
      <ItemFormDialog
        mode="edit"
        item={editing ?? undefined}
        open={editing !== null}
        onOpenChange={(open) => !open && setEditing(null)}
      />

      {/* 削除確認 Dialog */}
      <DeleteItemDialog
        item={deleting}
        onOpenChange={(open) => !open && setDeleting(null)}
      />
    </div>
  );
}