// フォーム入力 (state) を扱うので Client Component にする
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Controller, useForm } from "react-hook-form";
import { standardSchemaResolver } from "@hookform/resolvers/standard-schema";
import { z } from "zod";

import { apiClient } from "@/lib/api/client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Field,
  FieldError,
  FieldGroup,
  FieldLabel,
} from "@/components/ui/field";

// フォームの入力スキーマ (Zod で定義 → 型推論で LoginFormValues を生成)
const loginSchema = z.object({
  username: z.string().min(1, "ユーザー名は必須です"),
  password: z.string().min(1, "パスワードは必須です"),
});

type LoginFormValues = z.infer<typeof loginSchema>;

// page.tsx から import { LoginForm } で呼び出される (名前付き export)
export function LoginForm() {
  const router = useRouter();
  const [submitError, setSubmitError] = useState<string | null>(null);

  const form = useForm<LoginFormValues>({
    resolver: standardSchemaResolver(loginSchema),
    defaultValues: { username: "", password: "" },
  });

  const onSubmit = async (values: LoginFormValues) => {
    setSubmitError(null);

    // openapi-fetch クライアント。body の型は schema.ts の UserLogin に自動で絞り込まれる
    const { data, error } = await apiClient.POST("/api/v1/login", {
      body: values,
    });

    if (error) {
      // 401 (認証失敗) や 422 (バリデーション失敗) など
      setSubmitError(
        typeof error.detail === "string"
          ? error.detail
          : "ログインに失敗しました",
      );
      return;
    }

    // リクエストが成功すると backend が Set-Cookie: access_token=...; HttpOnly; SameSite=Lax ヘッダを返す
    // -> ブラウザが自動でCookieに保存 & 以降のリクエストに自動付与するので、frontend でCookieを操作する必要はない
    // -> HttpOnly Cookie はブラウザ JS から読めないため、 XSS で盗まれるリスクも減る
    void data;
    // ログイン成功後にトップへ遷移
    router.push("/");
  };

  return (
    <form
      onSubmit={form.handleSubmit(onSubmit)}
      className="space-y-4"
      noValidate
    >
      <FieldGroup>
        <Controller
          control={form.control}
          name="username"
          render={({ field, fieldState }) => (
            // data-invalid: エラー時に "true"
            // Tailwind の data-[invalid=true]: で見た目切替
            <Field data-invalid={fieldState.invalid}>
              {/* htmlFor で <Input id="..."> と紐付け、スクリーンリーダーがラベルと入力をペア認識できるように */}
              <FieldLabel htmlFor="login-username">ユーザー名</FieldLabel>
              <Input
                id="login-username"
                // ブラウザのパスワードマネージャがフォームを認識するためのヒント
                autoComplete="username"
                // aria-invalid: 支援技術 (スクリーンリーダー) 向けにエラー状態を伝える
                // data-invalid (見た目用) と役割を分けて両方付ける
                aria-invalid={fieldState.invalid}
                {...field}
              />
              {fieldState.invalid && (
                // errors は配列で渡す (複数エラーをまとめて表示できる API のため)
                <FieldError errors={[fieldState.error]} />
              )}
            </Field>
          )}
        />

        <Controller
          control={form.control}
          name="password"
          render={({ field, fieldState }) => (
            <Field data-invalid={fieldState.invalid}>
              <FieldLabel htmlFor="login-password">パスワード</FieldLabel>
              <Input
                id="login-password"
                type="password"
                autoComplete="current-password"
                aria-invalid={fieldState.invalid}
                {...field}
              />
              {fieldState.invalid && (
                <FieldError errors={[fieldState.error]} />
              )}
            </Field>
          )}
        />
      </FieldGroup>

      {submitError && (
        <p className="text-sm text-red-600" role="alert">
          {submitError}
        </p>
      )}

      <Button
        type="submit"
        className="w-full"
        // 送信中は二重送信防止のために無効化
        disabled={form.formState.isSubmitting}
      >
        {form.formState.isSubmitting ? "送信中..." : "ログイン"}
      </Button>
    </form>
  );
}