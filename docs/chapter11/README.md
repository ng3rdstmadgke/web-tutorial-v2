# Chapter 11: OpenAPI 駆動の型生成 + ログインページの実装

[<- 目次に戻る](../README.md)

## この章のゴール

- **[`openapi-typescript`](https://openapi-ts.dev/)** で FastAPI が出力する OpenAPI 仕様から TypeScript の型を自動生成できます (`pnpm gen:api`)
- **[`openapi-fetch`](https://openapi-ts.dev/openapi-fetch/)** で **型安全な fetch クライアント** を実装し、backend を呼べます
- Server Component / Client Component / middleware それぞれで適切な API ベース URL を **環境変数で出し分け** られます
- **[React Hook Form](https://react-hook-form.com/)** と **[Zod](https://zod.dev/)** でフォームのバリデーションを書けます
- **[shadcn/ui の `<Form>`](https://ui.shadcn.com/docs/components/form)** で見た目を整えたログインページを作れます
- **[Next.js middleware](https://nextjs.org/docs/app/api-reference/file-conventions/middleware)** で Cookie ベースの認証ガードを実装できます

## スタート地点

```bash
git checkout chapter11-start
```

## 完成形

```bash
git checkout chapter11-end
```

---

## はじめに

Chapter 10 で frontend (Next.js) を `docker compose up` できる状態にしました。ただ、現時点では backend (FastAPI) と完全に独立していて、API を叩く準備が整っていません。この章では：

1. **`openapi-typescript`** で backend の OpenAPI 仕様から TypeScript 型を生成し、
2. **`openapi-fetch`** で型安全な fetch クライアントを作り、
3. **ログインページ** を実装し、
4. **認証 middleware** で未ログインユーザーを `/login` にリダイレクトする、

までを一気通貫で行います。Chapter 6 で実装した backend の `POST /api/v1/login` (Cookie に JWT をセット) を、 frontend 側から型安全に呼び出せる状態がゴールです。

### なぜ OpenAPI 駆動の型生成か

backend と frontend を別々の TypeScript / Python プロジェクトとして書くと、**「backend のレスポンス型」と「frontend が期待する型」が一致しているか** は人力でしか確かめられません。たとえば backend で `User.email` というフィールドを足しても、 frontend は気付かず古いまま fetch して `data.email` が undefined、というケースが起きがちです。

FastAPI は Pydantic の型情報から **[OpenAPI 仕様](https://www.openapis.org/)** を自動生成します（`http://localhost:8000/openapi.json` で取得できる JSON）。これを **`openapi-typescript`** で TypeScript の型に変換すれば、 frontend は backend の真の型を「機械的に」共有できます：

```
FastAPI (Pydantic)
   |
   v (FastAPI が自動生成)
openapi.json
   |
   v (openapi-typescript)
src/lib/api/schema.ts  <-- TypeScript の型として frontend に届く
   |
   v (openapi-fetch)
client.GET / client.POST / ... <-- 引数・戻り値が型チェックされる
```

`backend/app/schemas.py` を 1 行変えると、`pnpm gen:api` を実行するだけで TypeScript 側の型も更新され、フィールドの抜けや型違いが **コンパイル時に検出される** ようになります。これが「OpenAPI 駆動」の本質です。

---

## この章で作るファイル

```
web-tutorial-v2/
├── compose.yaml                            # <- frontend に environment を追加
├── frontend/
│   ├── .env.example                        # <- 今回新規
│   ├── package.json                        # <- 依存追加 + scripts に gen:api
│   └── src/
│       ├── app/
│       │   └── login/page.tsx              # <- 今回新規 (Client Component)
│       ├── components/ui/
│       │   ├── form.tsx                    # <- shadcn add form
│       │   ├── input.tsx                   # <- shadcn add input
│       │   └── label.tsx                   # <- shadcn add label
│       ├── lib/api/
│       │   ├── client.ts                   # <- 今回新規 (openapi-fetch クライアント)
│       │   └── schema.ts                   # <- 今回新規 (openapi-typescript 生成物)
│       └── middleware.ts                   # <- 今回新規 (認証ガード)
```

---

## 1. openapi-typescript で型生成

### 1.1 インストール

```bash
cd $PROJECT_DIR/frontend

# CLI / 型生成用の devDependency として追加
pnpm add -D openapi-typescript
```

実行後、`frontend/package.json` の `devDependencies` に `openapi-typescript@^7.x` が入ります。本チュートリアルでは **`^7.13.0`** で動作確認しています。

> 公式ドキュメント: [openapi-typescript | openapi-ts](https://openapi-ts.dev/)

### 1.2 生成スクリプトを package.json に登録

毎回 CLI 引数を打つのは面倒なので、`pnpm gen:api` 1 コマンドで型生成できるよう `frontend/package.json` の `scripts` に登録します。

```json
{
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "eslint",
    "gen:api": "openapi-typescript http://web-tutorial-v2-backend-${HOST_USER}:8000/openapi.json -o src/lib/api/schema.ts"
  }
}
```

ポイント解説：

- **URL は Dev Container 内通信を使う**: `http://web-tutorial-v2-backend-${HOST_USER}:8000` は Chapter 10 のネットワーク補足で見た **同一 Docker ネットワーク内のコンテナ名** での名前解決です。`pnpm gen:api` は Dev Container のターミナルで実行する想定なので、コンテナ名でアクセスできます
- **`${HOST_USER}`** は Dev Container の `containerEnv` で定義されている環境変数。シェル経由で展開されます
- **出力先 `src/lib/api/schema.ts`** … 自動生成物。生成スクリプトを走らせるたびに上書きされるので、手で編集はしません

### 1.3 型を生成する

ディレクトリを用意してから実行します。

```bash
cd $PROJECT_DIR/frontend
mkdir -p src/lib/api

# 型を生成
pnpm gen:api
# ✨ openapi-typescript 7.13.0
# 🚀 http://web-tutorial-v2-backend-ktamido:8000/openapi.json -> src/lib/api/schema.ts [...ms]
```

生成された `src/lib/api/schema.ts` を覗いてみましょう。だいたい以下のような構造になっています（抜粋）：

```ts
// frontend/src/lib/api/schema.ts (抜粋)

export interface paths {
  "/api/v1/users/": {
    get: operations["read_users_api_v1_users__get"];
    post: operations["create_user_api_v1_users__post"];
    // ...
  };
  "/api/v1/login": {
    post: operations["login_api_v1_login_post"];
  };
  // ...
}

export interface components {
  schemas: {
    UserLogin: {
      username: string;
      password: string;
    };
    UserRead: {
      id: number;
      username: string;
      // ...
    };
    // ...
  };
}

export interface operations {
  login_api_v1_login_post: {
    requestBody: {
      content: { "application/json": components["schemas"]["UserLogin"] };
    };
    responses: {
      200: { content: { "application/json": unknown } };
      422: { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
    };
  };
  // ...
}
```

- **`paths`** … エンドポイントのパス文字列をキーとした、HTTP メソッドごとの operations 参照
- **`components.schemas`** … Pydantic モデルから生成された型 (`UserLogin`、`UserRead`、`ItemRead` など)
- **`operations`** … 各エンドポイントの `requestBody` / `responses` / `parameters` を細かく型付けしたもの

> **`schema.ts` を git にコミットするかどうか?**  
> **コミットすることをおすすめします**。生成物ですが、これがあるおかげで `pnpm install` 直後でも型補完が効きます。代わりに `pnpm gen:api` を **CI でも実行して、コミットされた `schema.ts` と差分が出ないことを確認** する運用がベストプラクティスです（Chapter 15 で CI 化します）。

---

## 2. openapi-fetch で型安全な fetch クライアント

### 2.1 インストール

```bash
cd $PROJECT_DIR/frontend
pnpm add openapi-fetch
```

本チュートリアルでは **`openapi-fetch@^0.17.0`** で動作確認しています。

> 公式ドキュメント: [openapi-fetch | openapi-ts](https://openapi-ts.dev/openapi-fetch/)

### 2.2 クライアントを作成する

`frontend/src/lib/api/client.ts` を新規作成します。

```bash
touch $PROJECT_DIR/frontend/src/lib/api/client.ts
```

```ts
// frontend/src/lib/api/client.ts
import createClient from "openapi-fetch";
import type { paths } from "./schema";

/**
 * API クライアントのベース URL を解決する。
 *
 * - サーバー側 (Server Component / Route Handler / middleware) では
 *   コンテナ間通信を使う必要があるので INTERNAL_API_URL を使う。
 * - クライアント側 (ブラウザで実行される Client Component) では
 *   ホスト OS から見える NEXT_PUBLIC_API_URL を使う。
 *
 * `NEXT_PUBLIC_` で始まる環境変数だけがクライアントバンドルに展開されるので、
 * INTERNAL_API_URL がブラウザに漏れる心配はない。
 */
function resolveBaseUrl(): string {
  if (typeof window === "undefined") {
    const url = process.env.INTERNAL_API_URL;
    if (!url) throw new Error("INTERNAL_API_URL is not set");
    return url;
  }
  const url = process.env.NEXT_PUBLIC_API_URL;
  if (!url) throw new Error("NEXT_PUBLIC_API_URL is not set");
  return url;
}

export const apiClient = createClient<paths>({
  baseUrl: resolveBaseUrl(),
  credentials: "include",
});
```

ポイント解説：

- **`createClient<paths>({ ... })`** … `paths` 型を渡すことで、 `apiClient.POST("/api/v1/login", ...)` の **第1引数は backend が公開しているパス文字列のユニオン型に限定** され、 `body` や `params` の型もそのパスに対応するものに自動で絞られます
- **`credentials: "include"`** … fetch のデフォルトは `same-origin`（Cookie を同一オリジン以外には送らない）です。frontend (`localhost:3000`) と backend (`localhost:8000`) はポートが違うので「クロスオリジン」扱いになり、`include` を指定しないと **Cookie が送信されません**。backend 側で `allow_credentials=True` の CORS 設定が必要なのと対になっています
- **`resolveBaseUrl()`** … サーバー側で実行されたか、ブラウザで実行されたかを `typeof window === "undefined"` で判定し、参照する環境変数を切り替えます。理由は次の Section 3 で詳しく解説します

### 2.3 使い方の感覚

実際の使用例（次の Section 6 でログインフォームに組み込みます）：

```ts
import { apiClient } from "@/lib/api/client";

const { data, error } = await apiClient.POST("/api/v1/login", {
  body: { username: "sys_admin", password: "admin" },
});

if (error) {
  // error の型は backend が定義した 401/422 のスキーマに絞られる
  console.error(error);
} else {
  // data の型は 200 レスポンスのスキーマに絞られる
  console.log(data.access_token);
}
```

- **`data` / `error` の discriminated union** … 成功レスポンス（2xx）は `data` に、エラーレスポンス（4xx / 5xx）は `error` に入ります。`if (error)` で型ガードすれば、`data` 側は `undefined` を排除して安全に使えます
- **パス文字列を変えるとエンドポイントの型も切り替わる** … `apiClient.POST("/api/v1/items/", ...)` と書くと、 body は `ItemCreate` 型になります

---

## 3. Server / Client 両用の API URL 戦略

ここまで `client.ts` に「Server 側なら `INTERNAL_API_URL`、Client 側なら `NEXT_PUBLIC_API_URL`」のロジックを書きました。なぜ 2 つの環境変数が必要なのか、構成図で整理します。

### 3.1 通信パターンの違い

```
                             ホスト OS
                             :3000      :8000
                               ▲          ▲
                               │          │
┌─ Host OS ───────────────────┼──────────┼─────────────────────────┐
│                              │          │                         │
│  ┌─────────────────┐  ┌──────┴──────┐  ┌┴───────────────┐         │
│  │ Dev Container   │  │ frontend    │  │ backend        │         │
│  │ (作業端末)      │  │ (Next.js)   │  │ (FastAPI)      │         │
│  │                 │  │  :3000      │  │  :8000         │         │
│  └────────┬────────┘  └──────┬──────┘  └────────┬───────┘         │
│           │                  │                  │                 │
│           │      (a) Server Component から fetch                   │
│           │           => INTERNAL_API_URL                          │
│           │           = http://web-tutorial-v2-backend-...:8000    │
│           │                  │                  │                 │
│           └──────────────────┼──────────────────┘                 │
│                              │                                    │
│             ┌────────────────┴───────────────┐                    │
│             │ Docker bridge network          │                    │
│             │ br-web-tutorial-v2-${HOST_USER}│                    │
│             └────────────────────────────────┘                    │
└─────────────────────────────────────────────────────────────────────┘
                               ▲
                               │ (b) Client Component (ブラウザ) から fetch
                               │     => NEXT_PUBLIC_API_URL
                               │     = http://localhost:8000
```

- **(a) Server Component / Route Handler / middleware から fetch するケース** … コードは **frontend コンテナの中** で実行されます。そこから backend を呼ぶには **Docker ネットワーク内のコンテナ名** (`http://web-tutorial-v2-backend-${HOST_USER}:8000`) でアクセスする必要があります。`localhost` を指定しても **frontend コンテナ自身の :8000 を見にいくだけ** で届きません
- **(b) Client Component（ブラウザ）から fetch するケース** … コードは **ホスト OS のブラウザ** で実行されます。ブラウザにとっての `localhost` はホスト OS なので、 `http://localhost:8000` でアクセスできます。逆にコンテナ名 (`web-tutorial-v2-backend-...`) は **ホスト OS では名前解決できません**

つまり、**同じ frontend のコードでも実行される場所によって backend の URL は別** にする必要があります。

### 3.2 環境変数の準備

`compose.yaml` の `frontend` サービスに `environment` を追加します。

```yaml
# compose.yaml
services:
  frontend:
    container_name: web-tutorial-v2-frontend-${HOST_USER}
    build:
      context: .
      dockerfile: docker/frontend.Dockerfile
    environment:                                                          # <- 追加
      INTERNAL_API_URL: http://web-tutorial-v2-backend-${HOST_USER}:8000  # <- 追加
      NEXT_PUBLIC_API_URL: http://localhost:8000                          # <- 追加
    ports:
      - "3000:3000"
    # ... 以下省略 ...
```

ポイント解説：

- **`INTERNAL_API_URL`** … Server 側で使う。コンテナ名を指している
- **`NEXT_PUBLIC_API_URL`** … Client 側で使う。**`NEXT_PUBLIC_` プレフィックス** が付いている環境変数は、Next.js がビルド時に **クライアントバンドルに値を直接埋め込みます**。これがないとブラウザに値が届きません

### 3.3 .env.example も用意する

`compose.yaml` で直接 environment を渡しているのでチュートリアル上は `.env` は必須ではありませんが、 学習者が後でローカル実行（コンテナ外）したい場合や、 README としての記録のために `.env.example` を置いておきます。

```bash
touch $PROJECT_DIR/frontend/.env.example
```

```dotenv
# frontend/.env.example

# Server Component / Route Handler / middleware からアクセスするときに使うベース URL
# (コンテナ間通信)
INTERNAL_API_URL=http://web-tutorial-v2-backend-CHANGEME:8000

# Client Component (ブラウザ) からアクセスするときに使うベース URL
# NEXT_PUBLIC_ で始まる変数はクライアントバンドルに展開される
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 3.4 環境変数を反映するために frontend を再起動

`compose.yaml` の `environment` を変更したので、frontend コンテナを再作成します（restart ではなく recreate が必要）。

```bash
cd $PROJECT_DIR

# 環境変数を読み直すために再作成
docker compose up -d frontend
```

> **`NEXT_PUBLIC_` 変数が反映されない場合**  
> Next.js は `NEXT_PUBLIC_` の値を **ビルド時に静的に置換** します。dev サーバー (`pnpm dev`) は環境変数の変更を再起動で拾いますが、ビルド済みのページキャッシュが残っているとブラウザに古い値が表示されることがあります。その場合は `docker compose down frontend && docker compose up -d frontend` でクリーンに作り直してください。

---

## 4. React Hook Form + Zod の基本

ログインページを作る前に、フォームライブラリの基本を押さえます。

### 4.1 インストール

```bash
cd $PROJECT_DIR/frontend
pnpm add react-hook-form zod @hookform/resolvers
```

本チュートリアルで動作確認しているバージョン：

| パッケージ | バージョン | 役割 |
|---|---|---|
| `react-hook-form` | `^7.75.0` | フォームの状態管理（[公式](https://react-hook-form.com/)） |
| `zod` | `^4.4.3` | スキーマ定義 + バリデーション（[公式](https://zod.dev/)）|
| `@hookform/resolvers` | `^5.2.2` | RHF と Zod を繋ぐアダプター |

### 4.2 Zod スキーマと型推論

Zod は **「ランタイムでのバリデーション + 静的な型」を同じ定義で書ける** ライブラリです：

```ts
import { z } from "zod";

const loginSchema = z.object({
  username: z.string().min(1, "ユーザー名は必須です"),
  password: z.string().min(1, "パスワードは必須です"),
});

// スキーマから TypeScript の型を取り出せる
type LoginFormValues = z.infer<typeof loginSchema>;
// => { username: string; password: string }
```

- **`z.object({...})`** … オブジェクトのスキーマ
- **`.min(1, "...")`** … 最小文字数のバリデーション + 失敗時のメッセージ
- **`z.infer<typeof schema>`** … スキーマから TypeScript の型を導出するヘルパー。**フォームの型を二重管理しなくて済む** のがポイント

### 4.3 React Hook Form の基本

```ts
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";

const form = useForm<LoginFormValues>({
  resolver: zodResolver(loginSchema),
  defaultValues: { username: "", password: "" },
});

const onSubmit = (values: LoginFormValues) => {
  // values は型安全（Zod の検証を通過した値）
};

// JSX 側で <form onSubmit={form.handleSubmit(onSubmit)}>...</form>
```

- **`zodResolver(loginSchema)`** … Zod スキーマを React Hook Form の `resolver` に変換するアダプター
- **`form.handleSubmit(onSubmit)`** … バリデーション通過時にだけ `onSubmit` を呼ぶ submit ハンドラを返す

これだけだと UI 部分が手書きになるので、次に shadcn/ui の `<Form>` コンポーネントと繋ぎ込みます。

---

## 5. shadcn/ui の `<Form>` を追加

shadcn/ui は **React Hook Form + Zod 前提のラッパー** として `<Form>` 一式を用意しています。これを追加すると、ラベル・入力欄・エラーメッセージが揃った見た目のフォームを宣言的に書けます。

### 5.1 コンポーネントを追加

```bash
cd $PROJECT_DIR/frontend

# Form / Input / Label を一括追加
pnpm dlx 'shadcn@^4.7.0' add form input label --yes
```

実行後、以下のファイルが配置されます：

| パス | 役割 |
|---|---|
| `src/components/ui/form.tsx` | `Form / FormField / FormItem / FormLabel / FormControl / FormMessage` の各パーツ |
| `src/components/ui/input.tsx` | 入力欄 |
| `src/components/ui/label.tsx` | ラベル |

> 公式ドキュメント: [Form | shadcn/ui](https://ui.shadcn.com/docs/components/form)

### 5.2 Form パーツの役割

`form.tsx` の中で公開されているコンポーネントを整理しておきます。

| パーツ | 役割 |
|---|---|
| `<Form {...form}>` | RHF の `form` インスタンスを Context で配下に共有する |
| `<FormField name="username" control={form.control} render={...}>` | 1 フィールド分の RHF Controller。`render` 関数の `field` を `<Input {...field} />` に渡す |
| `<FormItem>` | 1 フィールド分のラッパー（ラベル・入力・メッセージをグループ化） |
| `<FormLabel>` | `<label>` を出力。`htmlFor` は自動で `field.name` と紐付く |
| `<FormControl>` | 入力欄をラップして、エラー時に `aria-invalid` などのアクセシビリティ属性を当てる |
| `<FormMessage>` | Zod バリデーションのエラーメッセージを表示する |

---

## 6. ログインページを実装する

`src/app/login/page.tsx` を作成します。

```bash
mkdir -p $PROJECT_DIR/frontend/src/app/login
touch $PROJECT_DIR/frontend/src/app/login/page.tsx
```

```tsx
// frontend/src/app/login/page.tsx
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

import { apiClient } from "@/lib/api/client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";

// フォームの入力スキーマ
const loginSchema = z.object({
  username: z.string().min(1, "ユーザー名は必須です"),
  password: z.string().min(1, "パスワードは必須です"),
});

type LoginFormValues = z.infer<typeof loginSchema>;

export default function LoginPage() {
  const router = useRouter();
  const [submitError, setSubmitError] = useState<string | null>(null);

  const form = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { username: "", password: "" },
  });

  const onSubmit = async (values: LoginFormValues) => {
    setSubmitError(null);

    const { data, error } = await apiClient.POST("/api/v1/login", {
      body: values,
    });

    if (error) {
      // 401 (認証失敗) や 422 (バリデーション) など
      setSubmitError(
        typeof error.detail === "string"
          ? error.detail
          : "ログインに失敗しました",
      );
      return;
    }

    // 成功: backend が Set-Cookie で access_token を発行している
    // クライアントは特に何も保存する必要がない (HttpOnly Cookie)
    void data; // access_token はレスポンスにも返ってくるが、ブラウザでは Cookie 経由で使う
    router.push("/");
  };

  return (
    <main className="mx-auto max-w-sm p-8">
      <h1 className="text-3xl font-bold mb-6">Login</h1>

      <Form {...form}>
        <form
          onSubmit={form.handleSubmit(onSubmit)}
          className="space-y-4"
          noValidate
        >
          <FormField
            control={form.control}
            name="username"
            render={({ field }) => (
              <FormItem>
                <FormLabel>ユーザー名</FormLabel>
                <FormControl>
                  <Input autoComplete="username" {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="password"
            render={({ field }) => (
              <FormItem>
                <FormLabel>パスワード</FormLabel>
                <FormControl>
                  <Input
                    type="password"
                    autoComplete="current-password"
                    {...field}
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          {submitError && (
            <p className="text-sm text-red-600" role="alert">
              {submitError}
            </p>
          )}

          <Button
            type="submit"
            className="w-full"
            disabled={form.formState.isSubmitting}
          >
            {form.formState.isSubmitting ? "送信中..." : "ログイン"}
          </Button>
        </form>
      </Form>
    </main>
  );
}
```

### 解説

- **`"use client";`** … フォーム入力は React の state を扱うので Client Component です（Chapter 10 の 5.5 で見た `useState` / `useEffect` を含むコンポーネントの位置付け）
- **`apiClient.POST("/api/v1/login", { body: values })`** … `body` の型は backend の `UserLogin` スキーマに自動で絞り込まれます。`username` / `password` のキー以外を書こうとすると TypeScript エラーになります
- **`router.push("/")`** … ログイン成功後の遷移。`next/navigation` の `useRouter` を使います（Pages Router の `next/router` ではない点に注意）
- **Cookie は手動で扱わない** … backend がレスポンスに `Set-Cookie: access_token=...; HttpOnly; SameSite=Lax` を載せます。ブラウザは自動でこの Cookie を保存し、以降のリクエストに自動で含めるので、 frontend のコードでは何もしません
- **`autoComplete` 属性** … ブラウザのパスワードマネージャがフォームを認識できるよう、`username` / `current-password` を指定しています

---

## 7. 認証ガード (Next.js middleware)

ログインできても、未ログイン状態でも `/` にアクセスできてしまうと意味がありません。**Next.js の middleware** を使って、 Cookie に `access_token` が無いリクエストは `/login` にリダイレクトするようにします。

### 7.1 middleware.ts を作成

`src/middleware.ts` を新規作成します。

```bash
touch $PROJECT_DIR/frontend/src/middleware.ts
```

```ts
// frontend/src/middleware.ts
import { NextRequest, NextResponse } from "next/server";

// 認証なしでアクセスできるパス (login ページ自身など)
const PUBLIC_PATHS = ["/login"];

export function middleware(request: NextRequest) {
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

// middleware を適用するパスの絞り込み
// Next.js の内部パス・静的アセット・public 配下を除外
export const config = {
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico|.*\\.png$|.*\\.jpg$|.*\\.svg$).*)",
  ],
};
```

> 公式ドキュメント: [Middleware | Next.js](https://nextjs.org/docs/app/api-reference/file-conventions/middleware)

### 解説

- **`request.cookies.has("access_token")`** … Cookie の **有無のチェックだけ** を行います。JWT のデコードや署名検証は行いません
- **JWT を decode しない理由** … middleware は **Edge Runtime** で動くため、Node.js の `jsonwebtoken` 系のライブラリは使えません。署名検証用の `jose` などは動きますが、本チュートリアルでは **backend に検証責務を集約する** スタンスです。middleware は「Cookie がそもそも無いログイン前のユーザーを早期に弾く」役割に絞り、 Cookie に偽の値が入っているケースは backend が JWT 検証で 401 を返して弾きます
- **`matcher`** … middleware を実行するパスを正規表現で指定します。`_next/static` や画像ファイルは静的アセットなので除外しないと無駄なオーバーヘッドになります
- **`PUBLIC_PATHS`** … `/login` は未ログインユーザーがアクセスする必要があるので、 matcher に含まれていても明示的に通します

### 7.2 middleware の配置場所

Chapter 10 で `--src-dir` を指定したので、 **`src/middleware.ts`** に置きます（`src/app/middleware.ts` ではない点に注意）。`src/` を使わないプロジェクトの場合はプロジェクトルート直下に置きます。

---

## 8. 動作確認

### 8.1 backend に動作確認用のユーザーがいるか

Chapter 6 で seed していた管理者ユーザー (`sys_admin` / `admin`) を使ってログインを試します。`backend/.env` を `export` した状態で：

```bash
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "SELECT username FROM users;"
#  username
# -----------
#  sys_admin
# (1 row)
```

`sys_admin` が存在することを確認してください。無ければ Chapter 6 の `python -m app.seed_users` などで投入します。

### 8.2 ログインページを開く

ホスト OS のブラウザで http://localhost:3000/login にアクセスします。ユーザー名・パスワードのフォームが表示されます。

### 8.3 ログイン成功フロー

1. ユーザー名: `sys_admin` / パスワード: `admin` を入力して送信
2. ブラウザが `/` にリダイレクトされ、Home ページが表示される
3. DevTools の **Application** タブ → **Cookies** → `http://localhost:3000` を選ぶと、`access_token` Cookie が存在することを確認できる
   - `HttpOnly`: ✓
   - `SameSite`: Lax
4. DevTools の **Network** タブで `/api/v1/login` のリクエストを開き、 **Request Headers の `Content-Type: application/json`** と **Response Headers の `Set-Cookie: access_token=...`** が見える

### 8.4 ログイン失敗フロー

- ユーザー名・パスワードを間違えて送信 → フォーム下に `Incorrect username or password` が表示される
- 空欄で送信 → Zod の `「ユーザー名は必須です」` などのメッセージがフィールド下に表示される

### 8.5 認証ガード

1. DevTools → **Application** → **Cookies** → `access_token` を削除（または別ブラウザ・シークレットウィンドウで開く）
2. http://localhost:3000/ にアクセス
3. middleware が `/login` にリダイレクトしてくれる

### 8.6 ログアウト（おまけ）

現状ログアウトボタンを実装していませんが、 backend には `POST /api/v1/logout` があるので、 DevTools の Console から手動で叩けます：

```js
// ブラウザの Console で実行
await fetch("http://localhost:8000/api/v1/logout", {
  method: "POST",
  credentials: "include",
});
// 結果: access_token Cookie が削除される
```

その後リロードすると `/login` にリダイレクトされます。ログアウト UI は Chapter 12 のヘッダーレイアウトと一緒に整えます。

---

## まとめ

この章では以下を学びました：

- **`openapi-typescript` で OpenAPI → TypeScript 型生成**: `pnpm gen:api` 1 コマンドで `src/lib/api/schema.ts` が更新される
- **`openapi-fetch` で型安全な fetch クライアント**: `paths` を渡して `apiClient.POST("/api/v1/login", { body })` のように呼ぶと、 backend の Pydantic スキーマと一致した型補完が効く
- **Server / Client 両用の URL 戦略**: `INTERNAL_API_URL`（コンテナ間通信）と `NEXT_PUBLIC_API_URL`（ブラウザから）を環境変数で出し分け、`typeof window === "undefined"` で切り替え
- **`compose.yaml` の `frontend.environment`**: 環境変数の値はここで一元管理。 `NEXT_PUBLIC_` 接頭辞でクライアントバンドル展開される
- **React Hook Form + Zod**: スキーマ 1 つで「ランタイムバリデーション + TypeScript の型」を両取り。`useForm({ resolver: zodResolver(schema) })` パターン
- **shadcn/ui の `<Form>`**: `FormField` / `FormItem` / `FormLabel` / `FormControl` / `FormMessage` で宣言的にフォームを組む
- **ログインページ**: Client Component で `apiClient.POST("/api/v1/login")` を叩き、Cookie ベースで認証状態を保持
- **Next.js middleware**: Cookie の有無で `/login` にリダイレクト。JWT の中身検証は backend に集約

これで Cookie ベースの認証フローが一通り動く状態になりました。次の章では、認証済みユーザーが実際の CRUD 画面を操作できるようにしていきます。

## 次の章

[Chapter 12: CRUD 画面の実装 ->](../chapter12/README.md)

Chapter 12 では、Item・User の CRUD 画面を実装します。Server Component で初期データを取得し、Client Component から `TanStack Query` で更新・再取得を扱う構成にしていきます。
