import Link from "next/link";
import { Counter } from "@/components/Counter";
import { Button } from "@/components/ui/button";

export default function Home() {
  return (
    <main className="p-8">
      <h1 className="text-3xl font-bold">Hello Next.js</h1>
      <p className="mt-4">これは Next.js の App Router で作った最初のページです。</p>

      <div className="mt-4 flex gap-2">
        <Button>Default</Button>
        <Button variant="secondary">Secondary</Button>
        <Button variant="outline">Outline</Button>
        <Button variant="destructive">Destructive</Button>
        <Button variant="ghost">Ghost</Button>
      </div>

      <p className="mt-4">
        <Link href="/about" className="text-blue-500 underline">
          About ページへ
        </Link>
      </p>

      <div className="mt-8">
        <Counter />
      </div>
      <p className="mt-4">変数 <code>let foo = 1;</code> はインライン要素として Geist Mono が当たります</p>
      <div className="font-mono">この div も Geist Mono が当たります</div>
    </main>
  );
}