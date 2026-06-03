"use client";

import { useEffect } from "react";
import { Controller, useForm } from "react-hook-form";
import { standardSchemaResolver } from "@hookform/resolvers/standard-schema";
import { z } from "zod";

import { useSaveItem } from "@/feature/items/use-items";
import type { Item } from "@/feature/items/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Field,
  FieldError,
  FieldGroup,
  FieldLabel,
} from "@/components/ui/field";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

// backend の ItemCreate / ItemUpdate に合わせた入力ルール
const itemSchema = z.object({
  title: z.string().min(1, "タイトルは必須です").max(64, "64 文字以内で入力してください"),
  content: z.string().min(1, "内容は必須です").max(128, "128 文字以内で入力してください"),
});

type ItemFormValues = z.infer<typeof itemSchema>;

type Props = {
  mode: "create" | "edit";
  item?: Item; // edit のとき必須
  open: boolean;
  onOpenChange: (open: boolean) => void;
};

export function ItemFormDialog({ mode, item, open, onOpenChange }: Props) {
  const form = useForm<ItemFormValues>({
    resolver: standardSchemaResolver(itemSchema),
    defaultValues: { title: "", content: "" },
  });

  // Dialog を開くたびに、編集対象の値（or 空）をフォームへ流し込む
  useEffect(() => {
    if (open) {
      form.reset({ title: item?.title ?? "", content: item?.content ?? "" });
    }
  }, [open, item, form]);

  // 作成/編集の処理は feature のフックに集約。成功したら Dialog を閉じる
  const mutation = useSaveItem({
    mode,
    itemId: item?.id,
    onSuccess: () => onOpenChange(false),
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>
            {mode === "create" ? "アイテムを作成" : "アイテムを編集"}
          </DialogTitle>
        </DialogHeader>

        <form
          onSubmit={form.handleSubmit((values) => mutation.mutate(values))}
          className="space-y-4"
          noValidate
        >
          <FieldGroup>
            <Controller
              control={form.control}
              name="title"
              render={({ field, fieldState }) => (
                <Field data-invalid={fieldState.invalid}>
                  <FieldLabel htmlFor="item-title">タイトル</FieldLabel>
                  <Input id="item-title" aria-invalid={fieldState.invalid} {...field} />
                  {fieldState.invalid && <FieldError errors={[fieldState.error]} />}
                </Field>
              )}
            />
            <Controller
              control={form.control}
              name="content"
              render={({ field, fieldState }) => (
                <Field data-invalid={fieldState.invalid}>
                  <FieldLabel htmlFor="item-content">内容</FieldLabel>
                  <Input id="item-content" aria-invalid={fieldState.invalid} {...field} />
                  {fieldState.invalid && <FieldError errors={[fieldState.error]} />}
                </Field>
              )}
            />
          </FieldGroup>

          {mutation.isError && (
            <p className="text-sm text-red-600" role="alert">
              {mutation.error.message}
            </p>
          )}

          <DialogFooter>
            <Button type="submit" disabled={mutation.isPending}>
              {mutation.isPending ? "送信中..." : "保存"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
