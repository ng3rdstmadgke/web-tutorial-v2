import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export default function AboutPage() {
  return (
    <main className="p-8">
      <Card className="max-w-xl">
        <CardHeader>
          <CardTitle>About</CardTitle>
          <CardDescription>このアプリについて</CardDescription>
        </CardHeader>
        <CardContent>
          <p>
            このアプリは Web チュートリアル v2 のサンプルです。
            Next.js + Tailwind CSS + shadcn/ui で構成されています。
          </p>
        </CardContent>
      </Card>
    </main>
  );
}