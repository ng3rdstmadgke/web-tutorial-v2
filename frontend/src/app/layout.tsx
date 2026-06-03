import type { Metadata } from "next";
import { Inter, Noto_Sans_JP, Geist_Mono } from "next/font/google";
import { Providers } from "./providers";
import { Toaster } from "@/components/ui/sonner";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
});

const notoSansJP = Noto_Sans_JP({
  subsets: ["latin"],
  variable: "--font-noto-sans-jp",
});

const geistMono = Geist_Mono({
  subsets: ["latin"],
  variable: "--font-geist-mono",
});


export const metadata: Metadata = {
  title: "Web Tutorial v2",
  description: "Next.js + Tailwind + shadcn/ui のチュートリアル",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="ja"
      className={`${inter.variable} ${notoSansJP.variable} ${geistMono.variable}`}
    >
      <body>
        {/* TanStack Query のキャッシュをアプリ全体で共有 */}
        <Providers>{children}</Providers>
        {/* トーストの表示先。アプリのどこから toast(...) を呼んでもここに出る */}
        <Toaster />
      </body>
    </html>
  );
}