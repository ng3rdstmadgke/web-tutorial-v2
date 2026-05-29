"use client";

import { useRouter } from "next/navigation";
import { LogOut, Settings } from "lucide-react";

import { apiClient } from "@/lib/api/client";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import type { components } from "@/lib/api/schema";

// openapi-typescript で生成された UserRead 型を再利用。
// backend で UserRead が変わると frontend 側もコンパイル時に検出される
type User = components["schemas"]["UserRead"];

export function UserMenu({ user }: { user: User }) {
  const router = useRouter();

  const handleLogout = async () => {
    // backend が Set-Cookie: access_token=; Max-Age=0 で Cookie を削除する
    await apiClient.POST("/api/v1/logout");
    router.push("/login");
    // Server Component のキャッシュを破棄しないと、 layout.tsx で取得済みの user がキャッシュに残る
    router.refresh();
  };

  return (
    <DropdownMenu>
      {/*
        base-ui の render プロパティで、 DropdownMenuTrigger が出す <button> を <Button> で差し替える。
        子要素 (Avatar / span) は <Button> の中に展開される
        - `variant="ghost": 背景なし・ホバーで薄く色がつく
      */}
      <DropdownMenuTrigger
        render={
          <Button variant="ghost" className="flex items-center gap-2 px-2" />
        }
      >
        <Avatar className="h-7 w-7">
          <AvatarFallback>
            {user.username.charAt(0).toUpperCase()}
          </AvatarFallback>
        </Avatar>
        <span className="text-sm">{user.username}</span>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-48">
        {/* base-ui の DropdownMenuLabel / DropdownMenuItem は <Menu.Group> の中にいる必要があるので
            DropdownMenuGroup で必ず囲む */}
        <DropdownMenuGroup>
          <DropdownMenuLabel>{user.username}</DropdownMenuLabel>
          <DropdownMenuSeparator />
          <DropdownMenuItem onClick={() => router.push("/settings")}>
            <Settings className="mr-2 h-4 w-4" /> 設定
          </DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem onClick={handleLogout}>
            <LogOut className="mr-2 h-4 w-4" /> ログアウト
          </DropdownMenuItem>
        </DropdownMenuGroup>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}