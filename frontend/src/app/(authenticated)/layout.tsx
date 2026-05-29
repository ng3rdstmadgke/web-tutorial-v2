import { cookies } from "next/headers";
import Link from "next/link";
import { redirect } from "next/navigation";

import { apiClient } from "@/lib/api/client";
import {
  SidebarInset,
  SidebarProvider,
  SidebarTrigger,
} from "@/components/ui/sidebar";
import { TooltipProvider } from "@/components/ui/tooltip";

import { AppSidebar } from "./app-sidebar";
import { UserMenu } from "./user-menu";

async function fetchMe() {
  // Server Component から fetch するときは Cookie を手動で転送する必要がある
  // (Client Component の credentials: "include" は使えない)。
  const cookieHeader = (await cookies()).toString();
  const { data, error } = await apiClient.GET("/api/v1/me", {
    headers: { Cookie: cookieHeader },
    // /me はログインユーザーごとに変わるので Next.js のデータキャッシュは無効化する
    cache: "no-store",
  });
  if (error || !data) return null;
  return data;
}

export default async function AuthenticatedLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const me = await fetchMe();

  // proxy.ts は Cookie の存在だけをチェックする。
  // 「Cookie はあるが JWT が無効 / 期限切れ」のケースを考慮して layout 側でも未認証のガードを置く
  // (未認証だと /me で backend が 401 を返す)
  if (!me) {
    redirect("/login");
  }

  return (
    // Sidebar が内部で Tooltip を使うので、 親に TooltipProvider が必要 (今回はtooltipの機能は使わない)
    // (shadcn add sidebar 実行時の注意書きにも記載)
    <TooltipProvider>
      {/* shadcn の Sidebar は開閉状態を Provider で共有。 defaultOpenで初回の開閉状態を指定。 */}
      <SidebarProvider defaultOpen={false}>
        <AppSidebar />
        {/* SidebarInset: サイドバー以外の本体領域。 SidebarTrigger: 開閉ボタン */}
        <SidebarInset>
          <header className="flex h-12 items-center gap-3 border-b px-4">
            <SidebarTrigger />
            {/* アプリ名クリックで Home (/) に戻る Web の慣例 */}
            <Link href="/" className="text-lg font-bold">
              Web Tutorial v2
            </Link>
            <div className="flex-1" />
            <UserMenu user={me} />
          </header>
          <main className="p-6">{children}</main>
        </SidebarInset>
      </SidebarProvider>
    </TooltipProvider>
  );
}