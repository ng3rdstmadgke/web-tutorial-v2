import Link from "next/link";
import type { Metadata } from "next";
import { Inter, Noto_Sans_JP, Geist_Mono, Geist } from "next/font/google";  // <- 追加
import "./globals.css";
import { cn } from "@/lib/utils";

const geist = Geist({subsets:['latin'],variable:'--font-sans'});

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
      className={cn(inter.variable, notoSansJP.variable, geistMono.variable, "font-sans", geist.variable)}
    >
      <body>
        <header className="border-b p-4">
          <nav className="flex gap-4">
            <Link href="/" className="font-bold">Home</Link>
            <Link href="/about">About</Link>
          </nav>
        </header>
        {children}
      </body>
    </html>
  );
}