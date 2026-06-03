"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
// 必要なアイコンだけを import (lucide-react は tree-shakable なので import しなかったアイコンはバンドルに含まれない)。
// LucideIcon はアイコンコンポーネントの型
import { Package, Users, type LucideIcon } from "lucide-react";

import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";

type MenuItem = {
  title: string;
  url: string;
  icon: LucideIcon;
};

const items: MenuItem[] = [
  { title: "Items", url: "/items", icon: Package },
  { title: "Users", url: "/users", icon: Users },
];

export function AppSidebar() {
  // 現在の URL を取得して isActive でメニューのハイライトを切り替える
  const pathname = usePathname();

  return (
    // collapsible="icon": 折り畳み時にラベルが消えてアイコンだけが残るスタイル ("offcanvas" を選ぶと閉じたときに完全に消えるドロワー型)
    <Sidebar collapsible="icon">
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Menu</SidebarGroupLabel>
          <SidebarMenu>
            {items.map((item) => (
              <SidebarMenuItem key={item.url}>
                {/*
                  render プロパティで <button> の代わりに Next.js の <Link> を当てて クライアントサイドナビゲーションにする
                  (shadcn v4 base-nova は base-ui ベースなので、 Radix UI の asChild ではなく base-ui の render プロパティを使う)
                */}
                <SidebarMenuButton
                  render={<Link href={item.url} />}
                  isActive={pathname === item.url}
                >
                  {/* SidebarMenuButton は子に <svg> + <span> がある前提のスタイル。 collapsible="icon" のとき <span> だけがフェードアウトしてアイコンが残る */}
                  <item.icon />
                  <span>{item.title}</span>
                </SidebarMenuButton>
              </SidebarMenuItem>
            ))}
          </SidebarMenu>
        </SidebarGroup>
      </SidebarContent>
    </Sidebar>
  );
}