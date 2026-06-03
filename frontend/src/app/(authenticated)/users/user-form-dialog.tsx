"use client";

import { useEffect, useMemo } from "react";
import { Controller, useForm } from "react-hook-form";
import { standardSchemaResolver } from "@hookform/resolvers/standard-schema";
import { z } from "zod";

import { useRoles, useSaveUser } from "@/feature/users/use-users";
import type { User } from "@/feature/users/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
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

// mode によってルールが変わる:
// - create: username 必須 / password 8 文字以上
// - edit  : username は読み取り専用なので検証しない / password は空なら変更なし
function buildSchema(mode: "create" | "edit") {
  return z.object({
    username:
      mode === "create"
        ? z.string().min(1, "ユーザー名は必須です")
        : z.string(),
    password:
      mode === "create"
        ? z.string().min(8, "パスワードは 8 文字以上で入力してください")
        : z
            .string()
            .refine(
              (v) => v === "" || v.length >= 8,
              "パスワードは 8 文字以上で入力してください",
            ),
    role_ids: z.array(z.number()).min(1, "ロールを 1 つ以上選択してください"),
  });
}

type UserFormValues = z.infer<ReturnType<typeof buildSchema>>;

type Props = {
  mode: "create" | "edit";
  user?: User; // edit のとき必須
  open: boolean;
  onOpenChange: (open: boolean) => void;
};

export function UserFormDialog({ mode, user, open, onOpenChange }: Props) {
  // ロールの選択肢（page.tsx で prefetch 済み）
  const { data: roles } = useRoles();

  const schema = useMemo(() => buildSchema(mode), [mode]);
  const form = useForm<UserFormValues>({
    resolver: standardSchemaResolver(schema),
    defaultValues: { username: "", password: "", role_ids: [] },
  });

  useEffect(() => {
    if (open) {
      form.reset({
        username: user?.username ?? "",
        password: "",
        role_ids: user?.roles.map((r) => r.id) ?? [],
      });
    }
  }, [open, user, form]);

  // 作成/編集の処理（mode によるボディ組み立て含む）は feature のフックに集約
  const mutation = useSaveUser({
    mode,
    userId: user?.id,
    onSuccess: () => onOpenChange(false),
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>
            {mode === "create" ? "ユーザーを作成" : "ユーザーを編集"}
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
              name="username"
              render={({ field, fieldState }) => (
                <Field data-invalid={fieldState.invalid}>
                  <FieldLabel htmlFor="user-username">ユーザー名</FieldLabel>
                  <Input
                    id="user-username"
                    // 編集時は username を変更させない
                    disabled={mode === "edit"}
                    aria-invalid={fieldState.invalid}
                    {...field}
                  />
                  {fieldState.invalid && <FieldError errors={[fieldState.error]} />}
                </Field>
              )}
            />

            <Controller
              control={form.control}
              name="password"
              render={({ field, fieldState }) => (
                <Field data-invalid={fieldState.invalid}>
                  <FieldLabel htmlFor="user-password">
                    パスワード
                    {mode === "edit" && "（変更する場合のみ入力）"}
                  </FieldLabel>
                  <Input
                    id="user-password"
                    type="password"
                    autoComplete="new-password"
                    aria-invalid={fieldState.invalid}
                    {...field}
                  />
                  {fieldState.invalid && <FieldError errors={[fieldState.error]} />}
                </Field>
              )}
            />

            <Controller
              control={form.control}
              name="role_ids"
              render={({ field, fieldState }) => (
                <Field data-invalid={fieldState.invalid}>
                  <FieldLabel>ロール</FieldLabel>
                  <div className="space-y-2">
                    {roles?.map((role) => {
                      const checked = field.value.includes(role.id);
                      return (
                        <label key={role.id} className="flex items-center gap-2">
                          <Checkbox
                            checked={checked}
                            onCheckedChange={(c) =>
                              field.onChange(
                                c === true
                                  ? [...field.value, role.id]
                                  : field.value.filter((id) => id !== role.id),
                              )
                            }
                          />
                          <span>{role.name}</span>
                        </label>
                      );
                    })}
                  </div>
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
