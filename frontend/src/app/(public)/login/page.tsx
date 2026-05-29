// 'use client' が無いので Server Component。
import type { Metadata } from "next";
import { LoginForm } from "./login-form";

// metadata の export は Server Component でのみ可能
// metadata: ブラウザのタブタイトルや SEO 用の meta タグを設定
export const metadata: Metadata = {
  title: "ログイン | Web Tutorial v2",
};

export default function LoginPage() {
  return (
    <main className="mx-auto max-w-sm p-8">
      <h1 className="text-3xl font-bold mb-6">Login</h1>
      {/* インタラクティブな部分は子の Client Component に閉じ込める */}
      <LoginForm />
    </main>
  );
}