import { redirect } from "next/navigation";

export default function HomePage() {
  // 認証済みユーザーのトップはアイテム管理画面とする
  redirect("/items");
}