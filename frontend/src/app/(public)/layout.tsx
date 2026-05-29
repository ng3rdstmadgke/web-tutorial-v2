import Link from "next/link";

export default function PublicLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    // min-h-screen flex flex-col + flex-1 でヘッダーを除いた高さを children に確保
    <div className="min-h-screen flex flex-col">
      <header className="border-b">
        <div className="flex h-12 items-center px-4">
          {/* ロゴクリックで Home に戻る Web 慣例 (未ログイン中は proxy で /login に戻る) */}
          <Link href="/" className="text-lg font-bold">
            Web Tutorial v2
          </Link>
        </div>
      </header>
      <div className="flex-1">{children}</div>
    </div>
  );
}