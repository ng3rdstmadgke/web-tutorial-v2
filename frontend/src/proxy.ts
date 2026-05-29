import { NextRequest, NextResponse } from "next/server";

// 認証なしでアクセスできるパス (login ページ自身など)
const PUBLIC_PATHS = ["/login"];

export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // 公開パスはそのまま通す
  if (PUBLIC_PATHS.some((p) => pathname === p || pathname.startsWith(`${p}/`))) {
    return NextResponse.next();
  }

  // Cookie に access_token があるかどうかだけチェック
  // (JWT の中身の検証は backend 側に任せる)
  const hasToken = request.cookies.has("access_token");

  if (!hasToken) {
    const loginUrl = new URL("/login", request.url);
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

// proxy を適用するパスの絞り込み
// Next.js の内部パス・静的アセット・public 配下を除外
export const config = {
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico|.*\\.png$|.*\\.jpg$|.*\\.svg$).*)",
  ],
};