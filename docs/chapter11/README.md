# Chapter 11: OpenAPI 駆動の型生成 + ログインページの実装

[<- 目次に戻る](../README.md)

## この章のゴール

- **[`openapi-typescript`](https://openapi-ts.dev/)** で FastAPI が出力する OpenAPI 仕様から TypeScript の型を自動生成できます (`pnpm gen:api`)
- **[`openapi-fetch`](https://openapi-ts.dev/openapi-fetch/)** で **型安全な fetch クライアント** を実装し、backend を呼べます
- Server Component / Client Component / proxy それぞれで適切な API ベース URL を **環境変数で出し分け** られます
- **[React Hook Form](https://react-hook-form.com/)** と **[Zod](https://zod.dev/)** でフォームのバリデーションを書けます
- **[shadcn/ui の `<Field>`](https://ui.shadcn.com/docs/components/base/field)** で見た目を整えたログインページを作れます
- **[Next.js Proxy](https://nextjs.org/docs/app/api-reference/file-conventions/proxy)** で Cookie ベースの認証ガードを実装できます

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
4. **認証 proxy** で未ログインユーザーを `/login` にリダイレクトする、

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
├── .gitignore                              # <- frontend/.env.sample の例外を追記
├── frontend/
│   ├── .env.sample                         # <- 今回新規 (テンプレート、git で管理)
│   ├── .env                                # <- envsubst で生成 (.gitignore 対象)
│   ├── package.json                        # <- 依存追加 + scripts に gen:api
│   └── src/
│       ├── app/
│       │   ├── layout.tsx                  # <- 既存 Header の <nav> を取り除いて薄くする
│       │   ├── (public)/                   # <- 今回新規 (Route Group。未ログインエリア)
│       │   │   ├── layout.tsx              # <- 今回新規 (アプリ名のみのシンプルヘッダー)
│       │   │   └── login/
│       │   │       ├── page.tsx            # <- 今回新規 (フォーム本体だけ)
│       │   │       └── login-form.tsx      # <- 今回新規 (Client Component)
│       │   └── (authenticated)/            # <- 今回新規 (Route Group。認証必須エリア)
│       │       ├── layout.tsx              # <- 今回新規 (Sidebar + Header + UserMenu)
│       │       ├── app-sidebar.tsx         # <- 今回新規 (Sidebar 本体。Client Component)
│       │       ├── user-menu.tsx           # <- 今回新規 (アカウント DropdownMenu。Client Component)
│       │       ├── page.tsx                # <- src/app/page.tsx から移動
│       │       └── about/page.tsx          # <- src/app/about/page.tsx から移動
│       ├── components/ui/
│       │   ├── field.tsx                   # <- shadcn add field
│       │   ├── input.tsx                   # <- shadcn add input
│       │   ├── label.tsx                   # <- shadcn add label (field と同時に入る)
│       │   ├── separator.tsx               # <- shadcn add field の付属
│       │   ├── sidebar.tsx                 # <- shadcn add sidebar
│       │   ├── sheet.tsx                   # <- sidebar の依存
│       │   ├── tooltip.tsx                 # <- sidebar の依存
│       │   ├── skeleton.tsx                # <- sidebar の依存
│       │   ├── dropdown-menu.tsx           # <- shadcn add dropdown-menu
│       │   └── avatar.tsx                  # <- shadcn add avatar
│       ├── hooks/
│       │   └── use-mobile.ts               # <- sidebar の依存 (モバイル判定 hook)
│       ├── lib/api/
│       │   ├── client.ts                   # <- 今回新規 (openapi-fetch クライアント)
│       │   └── schema.ts                   # <- 今回新規 (openapi-typescript 生成物)
│       └── proxy.ts                        # <- 今回新規 (認証ガード。Next.js 16 で middleware.ts から改名)
```

---

## 1. openapi-typescript で型生成

- [openapi-typescript | openapi-ts](https://openapi-ts.dev/)

### 1.1 インストール

```bash
cd $PROJECT_DIR/frontend

# CLI / 型生成用の devDependency として追加
pnpm add -D 'openapi-typescript@^7.13.0'
```


### 1.2 生成スクリプトを package.json に登録

毎回 CLI 引数を打つのは面倒なので、`pnpm gen:api` 1 コマンドで型生成できるよう `frontend/package.json` の `scripts` に登録します。

```js
{
  // ...
  "scripts": {
    // ...
    // backendサーバーの openapi.json を参照して、APIクライアントの型定義を生成するコマンド
    "gen:api": "openapi-typescript http://web-tutorial-v2-backend-${HOST_USER}:8000/openapi.json -o src/lib/api/schema.ts"
  }
  // ...
}
```

### 1.3 型を生成する

`pnpm gen:api` は **backend の `/openapi.json` を HTTP で取得する** ので、 まず backend を起動しておく必要があります。

```bash
cd $PROJECT_DIR

# 環境変数 (Chapter 3 で作った .env) を export
export $(grep -v '^#' $PROJECT_DIR/backend/.env | xargs)

# 既存コンテナを止めて、最新のソース・設定で再ビルドして起動
docker compose down
docker compose up -d --build

# backend の OpenAPI 仕様が取得できることを確認
curl -s http://web-tutorial-v2-backend-${HOST_USER}:8000/openapi.json | jq '.info'
# {
#   "title": "FastAPI",
#   "version": "0.1.0"
# }
```

OpenAPI 仕様が返ってくれば準備完了です。続けて型生成を実行します。

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

## 2. Server / Client 両用の API URL 戦略


### 2.1 通信パターンの違い

backendのAPIサーバーへの通信パターンは2パターンあります。どこから呼び出すかで通信の宛先が変わるため、呼び出す場所で宛先が自動的に切り替わる仕組みを実装します。

```
                              ┌────────────────┐
                              │    Browser     │
                   ┌─────────▶│                │
                   │          │                │
                   │          └───────┬────────┘
               (HTML,JS)              │ (b) ブラウザ(Client Component) から backend のAPIにアクセス
                   │                  │ (http://localhost:8000)
                   │                  │
┌─ Host OS ────────┼──────────────────┼──────────────────────────────────────────┐
│                  │                  ▼                                          │
│           ┌──────┴──────┐  ┌────────────────┐                                  │
│           │ frontend    │  │ backend        │                                  │
│           │ (Next.js)   │  │ (FastAPI)      │                                  │
│           │  :3000      │  │  :8000         │                                  │
│           └──────┬──────┘  └────────────────┘                                  │
│                  │                  ▲                                          │
│                  │                  │                                          │
│                  └──────────────────┘                                          │
│               (a) frontend の Server Component から backend のAPIにアクセス       │
│               (http://web-tutorial-v2-backend-${HOST_USER}:8000)               │
└────────────────────────────────────────────────────────────────────────────────┘
```

- **(a) Server Component から backend のAPIにアクセス**  
  **frontend コンテナ -> backendコンテナ** への通信となるため、**Docker ネットワーク内のコンテナ名** (`http://web-tutorial-v2-backend-${HOST_USER}:8000`) でアクセスします。
- **(b) ブラウザからbackendのAPIにアクセス**  
  **ブラウザ -> ホストOSの8000ポート** への通信となるため、`http://localhost:8000` でアクセスします。


### 2.2 .env.sample を用意する

2パターンの

```bash
touch $PROJECT_DIR/frontend/.env.sample
```

```bash
# frontend/.env.sample

# [frontend の Server Component] -> [backend の API] へのアクセスで使うベース URL (コンテナ間通信)
INTERNAL_API_URL=http://web-tutorial-v2-backend-${HOST_USER}:8000

# [ブラウザ(Client Component)] -> [backend の API] へのアクセスで使うベース URL
# NEXT_PUBLIC_ プレフィックスはビルド時にクライアントバンドルへ値が展開される (= ブラウザに公開される)
NEXT_PUBLIC_API_URL=http://localhost:8000
```

> [!CAUTION] `NEXT_PUBLIC_` 系の値はブラウザに公開されます。 シークレットキー等の機密情報を含めてはいけません。


`frontend/.gitignore` で `.env.sample` を gitignore の対象から除外


```bash
# frontend/.gitignore

# .gitignore (frontend 部分)
.env*
!.env.sample
```

### 2.3 .env を生成する

```bash
# テンプレートから .env を生成する
envsubst < $PROJECT_DIR/frontend/.env.sample > $PROJECT_DIR/frontend/.env

# 生成された .env を確認
cat $PROJECT_DIR/frontend/.env
# INTERNAL_API_URL=http://web-tutorial-v2-backend-ktamido:8000
# NEXT_PUBLIC_API_URL=http://localhost:8000
```


### 2.4 compose.yaml で env_file として読み込む

`compose.yaml` の `frontend` サービスに `env_file` を追加します。

```yaml
# compose.yaml
services:
  frontend:
    container_name: web-tutorial-v2-frontend-${HOST_USER}
    build:
      context: .
      dockerfile: docker/frontend.Dockerfile
    env_file:                # <- 追加
      - frontend/.env        # <- 追加
    ports:
      - "3000:3000"
    # ... 以下省略 ...
```

### 2.5 T3Env で環境変数を型安全に扱う

- [`@t3-oss/env-nextjs`](https://env.t3.gg/)

ここまでで `process.env.INTERNAL_API_URL` のような形で環境変数を読めるようになりました。 ただし `process.env.X` の戻り値は **`string | undefined`** で、値が無い場合のチェックが各箇所で必要になります。また、Next.js 起動時に環境変数が足りなくてもエラーで落ちてくれません。(正常に起動したと誤認します)

Python の [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) のように **「環境変数を型安全に検証する」** ライブラリが Next.js にもあります。本チュートリアルでは **[`@t3-oss/env-nextjs`](https://env.t3.gg/)** を使います。

#### インストール

```bash
cd $PROJECT_DIR/frontend
pnpm add 'zod@^4.4.3' '@t3-oss/env-nextjs@^0.13.11'
```

依存として `zod` も必要ですが、 Section 4 (React Hook Form + Zod) で改めて追加するので、 ここでは `@t3-oss/env-nextjs` だけで OK です。

#### `src/lib/env.ts` を作成

```bash
mkdir -p $PROJECT_DIR/frontend/src/lib
touch $PROJECT_DIR/frontend/src/lib/env.ts
```

```ts
// frontend/src/lib/env.ts
import { createEnv } from "@t3-oss/env-nextjs";
import { z } from "zod";

// createEnv: @t3-oss/env-nextjs の Next.js 用ヘルパー
// 欠損や型違反があれば起動時に Invalid environment variables: { ... } で落ちる
export const env = createEnv({
  /**
   * サーバー側でのみ使う変数。Server Component / Route Handler / proxy から参照する。
   * NEXT_PUBLIC_ で始まる名前を書こうとすると型レベルでエラーになる。
   */
  server: {
    // z.url(): URL 形式の文字列であることを検証
    INTERNAL_API_URL: z.url(),
  },

  /**
   * クライアントに公開する変数。Client Component から参照する。
   * NEXT_PUBLIC_ で始まる名前以外を書こうとすると型レベルでエラーになる。
   */
  client: {
    NEXT_PUBLIC_API_URL: z.url(),
  },

  /**
   * 実際の値を渡す。
   */
  runtimeEnv: {
    INTERNAL_API_URL: process.env.INTERNAL_API_URL,
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
  },
});
```


これで `env.INTERNAL_API_URL` / `env.NEXT_PUBLIC_API_URL` のように、 **型が `string` に絞り込まれた** 値として参照できるようになりました。ここまでで環境変数の設定は完了です。次の 2.6 で frontend コンテナを再起動して反映させます。

### 2.6 環境変数を反映するために再起動

`compose.yaml` を変更し `.env` を新しく生成し、さらに `@t3-oss/env-nextjs` を依存に追加したので、コンテナを破棄して `--build` 付きで作り直します。

```bash
cd $PROJECT_DIR

# 環境変数を読み直すために、コンテナを破棄して --build 付きで作り直す
docker compose down
docker compose up -d --build
```

---

## 3. openapi-fetch で型安全な fetch クライアント

- [openapi-fetch | openapi-ts](https://openapi-ts.dev/openapi-fetch/)

### 3.1 インストール

```bash
cd $PROJECT_DIR/frontend
pnpm add 'openapi-fetch@^0.17.0'
```

### 3.2 クライアントを作成する

`frontend/src/lib/api/client.ts` を新規作成します。

```bash
touch $PROJECT_DIR/frontend/src/lib/api/client.ts
```

```ts
// frontend/src/lib/api/client.ts
import createClient from "openapi-fetch";
import type { paths } from "./schema";
import { env } from "@/lib/env";

/**
 * API クライアントのベース URL を解決する。
 *
 * - サーバー側 (Server Component) では、コンテナ間通信を使う必要があるので INTERNAL_API_URL を使う。
 * - クライアント側 (ブラウザで実行される Client Component) では、ホスト OS から見える NEXT_PUBLIC_API_URL を使う。
 */
function resolveBaseUrl(): string {
  // Server / Client で fetch する宛先 が異なるので、 window の存在で現在の実行場所を判定する。
  // - windowが存在=ブラウザ側
  // - windowが存在しない=サーバー側
  return typeof window === "undefined"
    ? env.INTERNAL_API_URL
    : env.NEXT_PUBLIC_API_URL;
}

// createClient に schema.ts の paths 型を渡すと、 第1引数は backend が公開しているパス文字列のユニオン型に限定され、 body / params もパスに対応する型に自動で絞られる
export const apiClient = createClient<paths>({
  baseUrl: resolveBaseUrl(),
  // fetch のデフォルトは "same-origin" (Cookie を同一オリジン以外に送らない)。
  // frontend(:3000) -> backend(:8000) のアクセスはクロスオリジン扱いなので Cookieを送信するには "include" 必須。
  // backend 側の CORS で allow_credentials=True が設定されているのと対になる。
  credentials: "include",
});
```

### 3.3 使い方の感覚

実際の使用例（次の Section 6 でログインフォームに組み込みます）：

```ts
import { apiClient } from "@/lib/api/client";

// 2xx は data に、 4xx/5xx は error に値が入る。
// パスに /api/v1/login を指定しているので、 body は UserLogin 型となる
const { data, error } = await apiClient.POST("/api/v1/login", {
  body: { username: "sys_admin", password: "admin" },
});

// if (error) で型ガードすれば、 data 側は undefined を排除して安全に使える。
if (error) {
  // error の型は backend が定義した 401/422 のスキーマに絞られる
  console.error(error);
} else {
  // data の型は 200 レスポンスのスキーマに絞られる
  console.log(data.access_token);
}
```

---

## 4. React Hook Form + Zod の基本

ログインページを作る前に、フォームライブラリの基本を押さえます。

### 4.1 インストール

```bash
cd $PROJECT_DIR/frontend
pnpm add 'react-hook-form@^7.75.0' '@hookform/resolvers@^5.2.2'
```

| パッケージ | 役割 |
|---|---|
| `react-hook-form` | フォームの状態管理（[公式](https://react-hook-form.com/)） |
| `zod` | スキーマ定義 + バリデーション（[公式](https://zod.dev/)）|
| `@hookform/resolvers` | React Hook Form と Zod を繋ぐアダプター |

### 4.2 Zod スキーマと型推論

Zod は **「ランタイムでのバリデーション + 静的な型」を同じ定義で書ける** ライブラリです：

```ts
import { z } from "zod";

//オブジェクトのスキーマを定義
const loginSchema = z.object({
  // .min(1, "..."): 最小文字数のバリデーション + 失敗時のメッセージ
  username: z.string().min(1, "ユーザー名は必須です"),
  password: z.string().min(1, "パスワードは必須です"),
});

// スキーマから TypeScript の型を導出できるので、フォーム用の型を二重管理しなくて済む
type LoginFormValues = z.infer<typeof loginSchema>; // -> { username: string; password: string }
```

> [!TIP] 公式ドキュメント
> - [Defining schemas | Zod](https://zod.dev/api) … 型指定
> - [Customizing errors | Zod](https://zod.dev/error-customization) … カスタムエラーメッセージ


### 4.3 React Hook Form の基本

> [!TIP] 公式ドキュメント
> - [useForm | React Hook Form](https://www.react-hook-form.com/api/useform/)


**[React Hook Form](https://react-hook-form.com/)** は、フォームの **入力値・エラー・送信状態** を管理するための React ライブラリです。 React Hook Form は **`useForm()` 1 つで `control` (フィールド接続のハンドル) / `handleSubmit` (送信ハンドラ) / `formState` (エラーや送信中フラグ) をまとめて提供** してくれます。


> [!TIP] 特徴：
> - **非制御コンポーネント (uncontrolled) ベース** … 内部で `ref` を使って DOM の値を直接読み書きするので、 入力のたびに親コンポーネントが再レンダリングされません。 大きなフォームでもパフォーマンスが落ちにくい
> - **バリデーションを resolver で外部化** … Zod / Valibot / Arktype 等のスキーマライブラリを **`resolver` 経由で差し込む** だけで、 バリデーションができます。 Zod v4 は **[Standard Schema](https://standardschema.dev/) 仕様** に準拠しているため、 `standardSchemaResolver` で繋ぎます。Standard Schema は Zod v4 / Valibot / Arktype など複数のスキーマライブラリが共通で実装する規格で、 1 つの resolver でどれにも切り替えられるのが利点です
> - **送信状態の管理** … `formState.isSubmitting` / `isDirty` / `isValid` などのフラグが揃っていて、「送信中はボタンを無効化」のような UI が簡単に書けます

```ts
import { useForm } from "react-hook-form";
import { standardSchemaResolver } from "@hookform/resolvers/standard-schema";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Field,
  FieldError,
  FieldGroup,
  FieldLabel,
} from "@/components/ui/field";

export function LoginForm() {
  // `control` (フィールド接続のハンドル) / `handleSubmit` (送信ハンドラ) / `formState` (エラーや送信中フラグ) がまとめられたオブジェクト
  const form = useForm<LoginFormValues>({
    // standardSchemaResolver: zodのスキーマを resolver(バリデーションを行うオブジェクト)に変換する
    resolver: standardSchemaResolver(loginSchema),
    defaultValues: { username: "", password: "" },
  });

  const onSubmit = (values: LoginFormValues) => {
    // formの送信処理
  };

  return (
    // form.handleSubmit: バリデーション通過時にだけ onSubmit を呼ぶ submit ハンドラを返す
    <form
      onSubmit={form.handleSubmit(onSubmit)}
      noValidate
    >
      <FieldGroup>
        {/* username の入力欄 */}
        <Controller
          control={form.control} // どのフォームに属するか
          name="username"        // どのフィールドか (Zod スキーマのキーと一致)
          render={({ field, fieldState }) => (
            // render は描画関数。 React Hook Form が用意した「フィールド接続部品」が引数に来る
            <Input {...field} />
          )}
        />

        {/* password の入力欄 */}
        <Controller
          control={form.control}
          name="password"
          render={({ field, fieldState }) => (
            <Input {...field} />
          )}
        />
      </FieldGroup>
      <Button
        type="submit"
        className="w-full"
        disabled={form.formState.isSubmitting} // 送信中は二重送信防止のために無効化
      >
        {form.formState.isSubmitting ? "送信中..." : "ログイン"}
      </Button>
    </form>
  );
}

```


#### `Controller` と `form.control` の役割

> [!TIP] 公式ドキュメント
> - [Controller | React Hook Form](https://www.react-hook-form.com/api/usecontroller/controller/)

`useForm()` が返す `form` オブジェクトには、`handleSubmit` / `formState` のほかに **`control`** というプロパティがあります。`control` は「**このフォームの状態を読み書きするためのハンドル**」で、 これを各フィールドに渡すことで、 React Hook Form は「どのフォームのどのフィールドか」を識別します。

**`Controller`** は、 **1フィールド分の React Hook Form 接続を担う React コンポーネント** です。たとえば「`username` フィールドを、 shadcn の `<Input>` に繋ぎたい」場合は以下のように記述します

```tsx
<Controller
  control={form.control}       // どのフォームに属するか
  name="username"              // どのフィールドか (Zod スキーマのキーと一致)
  render={({ field, fieldState }) => (
    // render は描画関数。 React Hook Form が用意した「フィールド接続部品」が引数に来る
    <Input {...field} />
  )}
/>
```

Controllerの属性の意味：

| 属性 | 役割 |
|---|---|
| **`control`** | `useForm()` が返した `form.control` を渡す。`Controller` がどのフォームに属するかを React Hook Form に伝える |
| **`name`** | フィールド名。Zod スキーマで定義したキー (`username` / `password`) と一致させる。型推論もここで効く |
| **`render`** | 「このフィールドの UI をどう描画するか」を返す関数。引数の `field` と `fieldState` を使って入力欄を組み立てる |

`render` の引数：

| 引数 | 中身 | 主な使い道 |
|---|---|---|
| **`field`** | `{ name, value, onChange, onBlur, ref }` のセット | `<Input {...field} />` のように **そのまま入力欄に spread** すると、 入力値が React Hook Form の state に自動で書き込まれる |
| **`fieldState`** | `{ invalid, error, isDirty, isTouched }` | バリデーション結果。 エラー表示の出し分け (`fieldState.invalid` / `fieldState.error`) |

---

## 5. shadcn/ui の `<Field>` を追加

shadcn/ui の **`Field`** コンポーネント群は、フォームの **「ラベル + 入力 + 説明文 + エラー」** をひとまとめに扱うためのプリミティブ群です。React Hook Form の `Controller` と組み合わせると、宣言的でアクセシビリティの整ったフォームを書けます。

> [!TIP] 公式ドキュメント:
> - [Field | shadcn/ui](https://ui.shadcn.com/docs/components/base/field)
> - [React Hook Form ガイド | shadcn/ui](https://ui.shadcn.com/docs/forms/react-hook-form)
> - [Input | shadcn/ui](https://ui.shadcn.com/docs/components/base/input)

### 5.1 コンポーネントを追加

```bash
cd $PROJECT_DIR/frontend

# Field を追加 (Label / Separator も依存として一緒に入る)
pnpm dlx 'shadcn@^4.7.0' add field --yes

# Input は別途追加 (Chapter 6 の login-form で使う)
pnpm dlx 'shadcn@^4.7.0' add input --yes
```

実行後、以下のファイルが配置されます：

| パス | 役割 |
|---|---|
| `src/components/ui/field.tsx` | `Field / FieldGroup / FieldLabel / FieldDescription / FieldError / FieldContent / FieldSet / FieldLegend / FieldSeparator` などのパーツ群 |
| `src/components/ui/label.tsx` | `<label>` のスタイル付きラッパー（既にあれば skip される） |
| `src/components/ui/separator.tsx` | フィールド間の区切り線（`field` の依存として入る） |
| `src/components/ui/input.tsx` | `<input>` のスタイル付きラッパー |

### 5.2 Field パーツの役割

主に使うパーツを整理しておきます。

| パーツ | 役割 |
|---|---|
| `<Field>` | 1 フィールド分のラッパー。`data-invalid` 属性でエラー状態を表現する |
| `<FieldLabel>` | `<label>` を出力。`htmlFor` で入力欄と紐付ける |
| `<FieldDescription>` | フィールドの補足説明（任意） |
| `<FieldError errors={[error]}>` | バリデーションエラーメッセージを表示 |
| `<FieldGroup>` | 複数の `<Field>` をまとめるグループ |
| `<FieldContent>` | 横並びレイアウト時に「ラベル + 説明 + エラー」のテキスト側をまとめるサブブロック |
| `<FieldSet>` / `<FieldLegend>` | 関連フィールドを囲む `<fieldset>` / `<legend>` 相当 |
| `<FieldSeparator>` | フィールド間の区切り線 |

---

## 6. ログインページを実装する

ログインページは **2 つのファイル** に分けて作ります。

| ファイル | 役割 | コンポーネントの種類 |
|---|---|---|
| `src/app/login/page.tsx` | URL `/login` のエントリポイント。メタデータ設定と `<LoginForm />` の配置だけ | **Server Component** |
| `src/app/login/login-form.tsx` | フォーム本体（Zod スキーマ・useForm・API 呼び出し） | **Client Component** |

> [!NOTE] 設計判断：なぜ 2 ファイルに分けるのか
> - **Client Component の境界を最小化する**: `'use client'` は「ここから先はクライアント側で動く」という境界線です。ページ全体に当てるとそのメリット（SSR されるツリーが減る）が失われるので、 **本当にインタラクティブな部分だけ** を Client Component に閉じ込めます
> - **コロケーション (使うルートに近い場所に置く)**: ログインフォームのコンポーネントは `/login` ルートでしか使わないので、 `app/login/` の中に置きます。複数のページから再利用するコンポーネント（例: ヘッダー）は `src/components/` 配下、 という使い分けです

### 6.1 ディレクトリと空ファイルを作る

```bash
mkdir -p $PROJECT_DIR/frontend/src/app/login
touch $PROJECT_DIR/frontend/src/app/login/page.tsx
touch $PROJECT_DIR/frontend/src/app/login/login-form.tsx
```

### 6.2 page.tsx (Server Component)

```tsx
// frontend/src/app/login/page.tsx

// 'use client' が無いので Server Component。
import type { Metadata } from "next";
import { LoginForm } from "./login-form";

// metadata の export は Server Component でのみ可能
// metadata: ブラウザのタブタイトルや SEO 用の meta タグを設定
export const metadata: Metadata = {
  title: "ログイン | Web Tutorial v2",
};

export default function LoginPage() {
  return (
    <main className="mx-auto max-w-sm p-8">
      <h1 className="text-3xl font-bold mb-6">Login</h1>
      {/* インタラクティブな部分は子の Client Component に閉じ込める */}
      <LoginForm />
    </main>
  );
}
```

### 6.3 login-form.tsx (Client Component)


#### 完成形のコード

```tsx
// frontend/src/app/login/login-form.tsx

// フォーム入力 (state) を扱うので Client Component にする
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Controller, useForm } from "react-hook-form";
import { standardSchemaResolver } from "@hookform/resolvers/standard-schema";
import { z } from "zod";

import { apiClient } from "@/lib/api/client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Field,
  FieldError,
  FieldGroup,
  FieldLabel,
} from "@/components/ui/field";

// フォームの入力スキーマ (Zod で定義 → 型推論で LoginFormValues を生成)
const loginSchema = z.object({
  username: z.string().min(1, "ユーザー名は必須です"),
  password: z.string().min(1, "パスワードは必須です"),
});

type LoginFormValues = z.infer<typeof loginSchema>;

// page.tsx から import { LoginForm } で呼び出される (名前付き export)
export function LoginForm() {
  const router = useRouter();
  const [submitError, setSubmitError] = useState<string | null>(null);

  const form = useForm<LoginFormValues>({
    resolver: standardSchemaResolver(loginSchema),
    defaultValues: { username: "", password: "" },
  });

  const onSubmit = async (values: LoginFormValues) => {
    setSubmitError(null);

    // openapi-fetch クライアント。body の型は schema.ts の UserLogin に自動で絞り込まれる
    const { data, error } = await apiClient.POST("/api/v1/login", {
      body: values,
    });

    if (error) {
      // 401 (認証失敗) や 422 (バリデーション失敗) など
      setSubmitError(
        typeof error.detail === "string"
          ? error.detail
          : "ログインに失敗しました",
      );
      return;
    }

    // リクエストが成功すると backend が Set-Cookie: access_token=...; HttpOnly; SameSite=Lax ヘッダを返す
    // -> ブラウザが自動でCookieに保存 & 以降のリクエストに自動付与するので、frontend でCookieを操作する必要はない
    // -> HttpOnly Cookie はブラウザ JS から読めないため、 XSS で盗まれるリスクも減る
    void data;
    // ログイン成功後にトップへ遷移
    router.push("/");
  };

  return (
    <form
      onSubmit={form.handleSubmit(onSubmit)}
      className="space-y-4"
      noValidate
    >
      <FieldGroup>
        <Controller
          control={form.control}
          name="username"
          render={({ field, fieldState }) => (
            // data-invalid: エラー時に "true"
            // Tailwind の data-[invalid=true]: で見た目切替
            <Field data-invalid={fieldState.invalid}>
              {/* htmlFor で <Input id="..."> と紐付け、スクリーンリーダーがラベルと入力をペア認識できるように */}
              <FieldLabel htmlFor="login-username">ユーザー名</FieldLabel>
              <Input
                id="login-username"
                // ブラウザのパスワードマネージャがフォームを認識するためのヒント
                autoComplete="username"
                // aria-invalid: 支援技術 (スクリーンリーダー) 向けにエラー状態を伝える
                // data-invalid (見た目用) と役割を分けて両方付ける
                aria-invalid={fieldState.invalid}
                {...field}
              />
              {fieldState.invalid && (
                // errors は配列で渡す (複数エラーをまとめて表示できる API のため)
                <FieldError errors={[fieldState.error]} />
              )}
            </Field>
          )}
        />

        <Controller
          control={form.control}
          name="password"
          render={({ field, fieldState }) => (
            <Field data-invalid={fieldState.invalid}>
              <FieldLabel htmlFor="login-password">パスワード</FieldLabel>
              <Input
                id="login-password"
                type="password"
                autoComplete="current-password"
                aria-invalid={fieldState.invalid}
                {...field}
              />
              {fieldState.invalid && (
                <FieldError errors={[fieldState.error]} />
              )}
            </Field>
          )}
        />
      </FieldGroup>

      {submitError && (
        <p className="text-sm text-red-600" role="alert">
          {submitError}
        </p>
      )}

      <Button
        type="submit"
        className="w-full"
        // 送信中は二重送信防止のために無効化
        disabled={form.formState.isSubmitting}
      >
        {form.formState.isSubmitting ? "送信中..." : "ログイン"}
      </Button>
    </form>
  );
}
```

> [!TIP] 公式ドキュメント
> - [Controller | React Hook Form](https://www.react-hook-form.com/api/usecontroller/controller/)
> - [useRouter | Next.js](https://nextjs.org/docs/app/api-reference/functions/use-router)
---

## 7. 認証ガード (Next.js Proxy)

ログインできても、未ログイン状態でも `/` にアクセスできてしまうと意味がありません。**Next.js の Proxy** (Next.js 15 まで「Middleware」と呼ばれていた仕組み) を使って、Cookie に `access_token` が無いリクエストは `/login` にリダイレクトするようにします。

### 7.1 proxy.ts を作成

> [!TIP] 公式ドキュメント
> - [Proxy | Next.js](https://nextjs.org/docs/app/api-reference/file-conventions/proxy)

`src/proxy.ts` を新規作成します。

```bash
touch $PROJECT_DIR/frontend/src/proxy.ts
```

```ts
// frontend/src/proxy.ts
import { NextRequest, NextResponse } from "next/server";

// 認証なしでアクセスできるパス。 matcher に含まれていても明示的に通す
const PUBLIC_PATHS = ["/login"];

export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // 公開パスはそのまま通す
  if (PUBLIC_PATHS.some((p) => pathname === p || pathname.startsWith(`${p}/`))) {
    return NextResponse.next();
  }

  // Cookie の有無のチェックだけ。 JWT の decode / 署名検証は backend に任せる。 (検証ロジックを2箇所で持たない)
  const hasToken = request.cookies.has("access_token");

  if (!hasToken) {
    const loginUrl = new URL("/login", request.url);
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

// Next.js の内部パス・画像系の静的アセットは除外する (無駄なオーバーヘッドを避ける)
export const config = {
  // matcher: proxy でアクセスを制限するパスを正規表現で指定
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico|.*\\.png$|.*\\.jpg$|.*\\.svg$).*)",
  ],
};
```

> [!NOTE] ポイント解説:
> - proxy.ts はサーバー側で評価されるため、HttpOnlyなCookieにもアクセス可能です。 (JSでHttpOnlyなCookieにアクセスできないのはブラウザの挙動)

---

## 8. 共通レイアウト (Sidebar + Header + アカウントメニュー)

ログインが通るようになったので、 認証済みユーザー向けの **共通レイアウト** を整えます。ヘッダーに **折り畳み可能なサイドメニュー** と **アカウントメニュー (ログアウト・設定)** を置く、 業務 Web アプリでよくある構成です。

### 8.1 設計方針

- **Route Group を利用して `(public)` と `(authenticated)` でエリアを分ける** … Route Group は ディレクトリ名を `()` で囲むことで、**URL に影響しない** ディレクトリでリソースを論理的に分割できる Next.js の機能  
  以下のように分割します。
  - `src/app/(public)/layout.tsx`: 未ログイン用のシンプルヘッダー
  - `src/app/(authenticated)/layout.tsx`: Sidebar + ヘッダー (Sidebar Trigger + アプリ名 + UserMenu)
- **shadcn/ui の `Sidebar`** … 折り畳み・モバイル時のドロワー化・キーボードショートカット (`Cmd/Ctrl+B`) などが組み込み済みの複合コンポーネント
- **`DropdownMenu` + `Avatar`** … アカウントのプルダウンメニュー
- **ユーザー情報は `(authenticated)/layout.tsx` (Server Component) で `GET /api/v1/me` を fetch** … サーバー側で取得すれば、 初回描画時にユーザー名が空欄からチラつくことがありません

> [!TIP] 公式ドキュメント:
> - [Sidebar | shadcn/ui](https://ui.shadcn.com/docs/components/base/sidebar)
> - [Dropdown Menu | shadcn/ui](https://ui.shadcn.com/docs/components/base/dropdown-menu)
> - [Avatar | shadcn/ui](https://ui.shadcn.com/docs/components/base/avatar)
> - [Route Groups | Next.js](https://nextjs.org/docs/app/api-reference/file-conventions/route-groups)

### 8.2 shadcn/ui のコンポーネントを追加

```bash
cd $PROJECT_DIR/frontend

# Sidebar (sheet / tooltip / skeleton / use-mobile.ts なども一緒に入る)
pnpm dlx 'shadcn@^4.7.0' add sidebar --yes
# The `tooltip` component has been added. Remember to wrap your app with the `TooltipProvider` component.
# 
# ```tsx title="app/layout.tsx"
# import { TooltipProvider } from "@/components/ui/tooltip"
# 
# export default function RootLayout({ children }: { children: React.ReactNode }) {
#   return (
#     <html lang="en">
#       <body>
#         <TooltipProvider>{children}</TooltipProvider>
#       </body>
#     </html>
#   )
# }
# ```


# Dropdown Menu と Avatar
pnpm dlx 'shadcn@^4.7.0' add dropdown-menu avatar --yes
```

`src/components/ui/` 配下に **7 個のコンポーネント** (`sidebar.tsx` / `sheet.tsx` / `tooltip.tsx` / `skeleton.tsx` / `dropdown-menu.tsx` / `avatar.tsx` と、すでにある `separator.tsx` の上書き判定) と、 **`src/hooks/use-mobile.ts`** が配置されます。

### 8.3 既存のページを Route Group に移動

ページを 2 つの Route Group に振り分けます。

| Route Group | 対象 | レイアウト |
|---|---|---|
| `(public)/` | `/login` (未ログインアクセス可能) | アプリ名だけのシンプルヘッダー |
| `(authenticated)/` | `/`, `/about` (認証必須) | Sidebar + ヘッダー (アプリ名 + UserMenu) |

Route Group はディレクトリ名が `()` で囲まれている場合に **URL に影響しない** Next.js の機能なので、 `/login` も `/about` も URL は変わりません。

```bash
# (public) に login を移動
mkdir -p $PROJECT_DIR/frontend/src/app/\(public\)
mv $PROJECT_DIR/frontend/src/app/login $PROJECT_DIR/frontend/src/app/\(public\)/login

# (authenticated) に Home / About を移動
mkdir -p $PROJECT_DIR/frontend/src/app/\(authenticated\)/about
mv $PROJECT_DIR/frontend/src/app/page.tsx $PROJECT_DIR/frontend/src/app/\(authenticated\)/page.tsx
mv $PROJECT_DIR/frontend/src/app/about/page.tsx $PROJECT_DIR/frontend/src/app/\(authenticated\)/about/page.tsx
rmdir $PROJECT_DIR/frontend/src/app/about
```

### 8.4 ルート `layout.tsx` を薄くする

ヘッダーは **未ログイン / 認証下** で見た目が変わるので、 root layout には置きません。Chapter 10 で実装した `<header>` 内のナビゲーションを削除し、 root layout は `<html>` / `<body>` だけにします。

```tsx
// frontend/src/app/layout.tsx
import type { Metadata } from "next";
import { Inter, Noto_Sans_JP, Geist_Mono } from "next/font/google";
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
      <body>{children}</body>
    </html>
  );
}
```

### 8.5 (public)/layout.tsx を作る

未ログインで開けるページ（現状は `/login` のみ）に共通のシンプルヘッダーを置きます。`src/app/(public)/layout.tsx` を新規作成します。

```bash
touch $PROJECT_DIR/frontend/src/app/\(public\)/layout.tsx
```

```tsx
// frontend/src/app/(public)/layout.tsx
// アプリ名だけのシンプルヘッダー。 /login 以外に将来 /signup や /forgot-password を
// 追加するときもこの layout がそのまま使える
import Link from "next/link";

export default function PublicLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    // min-h-screen flex flex-col + flex-1 でヘッダーを除いた高さを children に確保
    // min-h-screen: `min-height: 100vh` 要素の高さを最低でも画面（ビューポート：ユーザーがブラウザで今見ている表示領域）いっぱいにする
    // flex: `display: flex` 子要素を横や縦に整列させる
    // flex-col: `flex-direction: column` 子要素を縦に整列させる
    <div className="min-h-screen flex flex-col">
      <header className="border-b">
        <div className="flex h-12 items-center px-4">
          {/* ロゴクリックで Home に戻る Web 慣例 (未ログイン中は proxy で /login に戻る) */}
          <Link href="/" className="text-lg font-bold">
            Web Tutorial v2
          </Link>
        </div>
      </header>
      {/* flex-1: 残りのスペースを全て埋める */}
      <div className="flex-1">{children}</div>
    </div>
  );
}
```

> [!NOTE] `src/app/(public)/login/page.tsx` は **書き直し不要** です。 Section 6.2 で書いた `<main>` だけのシンプル構成のまま、 ヘッダーは親の `(public)/layout.tsx` が出してくれます。


> [!TIP] 公式ドキュメント
> - [min-height | Tailwind CSS](https://tailwindcss.com/docs/min-height)
> - [flex | Tailwind CSS](https://tailwindcss.com/docs/flex)
> - [flex-col | Tailwind CSS](https://tailwindcss.com/docs/flex-direction#column)

### 8.6 サイドバー本体を作る

`src/app/(authenticated)/app-sidebar.tsx` を新規作成します。サイドバー上部のアプリ名表記はヘッダーと重複するので置きません（メニュー項目だけにします）。各項目には **[`lucide-react`](https://lucide.dev/) のアイコン** を添えて、折り畳み時にもメニューが認識できるようにします。

> [!NOTE] **`lucide-react` について**  
> shadcn/ui の標準アイコンライブラリで、 Chapter 10 で `pnpm create next-app ... --react-compiler --yes` 後の `shadcn init --defaults` 実行時に既にインストール済みです。 アイコン名 [lucide.dev/icons](https://lucide.dev/icons/) で検索できます。 tree-shaking で `import` したアイコンのみバンドルに含まれます。

```bash
touch $PROJECT_DIR/frontend/src/app/\(authenticated\)/app-sidebar.tsx
```

```tsx
// frontend/src/app/(authenticated)/app-sidebar.tsx
"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
// 必要なアイコンだけを import (lucide-react は tree-shakable なので import しなかったアイコンはバンドルに含まれない)。
// LucideIcon はアイコンコンポーネントの型
import { Home, Info, type LucideIcon } from "lucide-react";

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
  { title: "Home", url: "/", icon: Home },
  { title: "About", url: "/about", icon: Info },
  // Chapter 12 以降で増やす想定
  // { title: "Items", url: "/items", icon: Package },
  // { title: "Users", url: "/users", icon: Users },
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
```

> [!TIP] アイコン選びのコツ  
> [Lucide のアイコン検索ページ](https://lucide.dev/icons/) で「box」「package」「user」「settings」などのキーワードで検索できます。コンポーネント名はパスカルケースで import 名になります（例: `box` -> `Box`、`user-plus` -> `UserPlus`）。

### 8.7 アカウントメニューを作る

`src/app/(authenticated)/user-menu.tsx` を新規作成します。

```bash
touch $PROJECT_DIR/frontend/src/app/\(authenticated\)/user-menu.tsx
```

```tsx
// frontend/src/app/(authenticated)/user-menu.tsx
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
```

### 8.8 (authenticated)/layout.tsx を作る

`src/app/(authenticated)/layout.tsx` を新規作成します。これは **Server Component** で、 `GET /api/v1/me` を取得して `<UserMenu>` に渡します。

```bash
touch $PROJECT_DIR/frontend/src/app/\(authenticated\)/layout.tsx
```

```tsx
// frontend/src/app/(authenticated)/layout.tsx
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
```

### 8.9 移動した page.tsx の中身を整える

Section 8.3 で移動した `(authenticated)/page.tsx` と `(authenticated)/about/page.tsx` は、 Chapter 10 で書いた内容そのままで動きます（パスは変わらないので import パスも変更不要）。

ただし `(authenticated)/page.tsx` の中で参照していた `@/components/Counter` は、`src/components/Counter.tsx` のままなので、 import パスもそのままで OK です。

> **`/settings` は未実装**  
> `UserMenu` の「設定」ボタンは `router.push("/settings")` を呼んでいますが、`/settings` ページはまだ無いので 404 になります。 Chapter 12 以降で実装します。空ページだけ用意して 404 を回避したい場合は `src/app/(authenticated)/settings/page.tsx` に最小の `<p>Coming Soon</p>` 等を置いてください。

---

## 9. 動作確認

### 9.1 再起動と DB の準備

コンテナをリビルドして再起動後、マイグレーションとシードデータの投入を行います。

```bash
cd $PROJECT_DIR

# コンテナを破棄して --build 付きで作り直す (frontend の environment 変更を反映)
docker compose down && docker compose up -d --build

sleep 5

# 環境変数の読み込み (DB接続用)
export $(grep -v '^#' $PROJECT_DIR/backend/.env | xargs)

cd $PROJECT_DIR/backend

# DB マイグレーションを適用 (users / items / roles / user_roles テーブルを作成)
uv run alembic upgrade head

# roles, 初期ユーザー の seed (Chapter 4 で作った冪等スクリプト)
uv run python -m app.seed

# ユーザーが入ったことを確認
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "SELECT username FROM users;"
#  username
# -----------
#  sys_admin
#  loc_admin
#  loc_operator
# (3 rows)
```

### 9.2 ログインフロー

- http://localhost:3000/ にアクセスして、http://localhost:3000/login にリダイレクトされることを確認します
- http://localhost:3000/login で `username: sys_admin` / `password: admin` を入力して送信
- 成功するとサイドバーとヘッダー付きの `/` (Home) に遷移します
- DevTools の **Application** -> **Cookies** -> **http://localhost:3000** で **access_token** Cookie が `HttpOnly` / `SameSite=Lax` で設定されていることを確認

### 9.3 共通レイアウトの確認

ログイン後の画面で：

- **左サイドバー** が表示され、`Home` / `About` のメニューが並んでいる
- ヘッダー左の **メニューアイコン (`SidebarTrigger`)** または **`Cmd / Ctrl + B`** でサイドバーが折り畳まれる
- 折り畳み時はアイコンだけが残る（`collapsible="icon"` 指定のため）
- ヘッダー右の **アバター + ユーザー名 (`sys_admin`)** が表示される
- `docker compose logs -f` でページロード時に `GET /api/v1/me` が叩かれ、 200 OK でレスポンスが返っていることを確認

### 9.4 ログアウト動作

1. ヘッダー右の **アバターをクリック** → ドロップダウンが開く
2. **「ログアウト」** をクリック
3. backend に `POST /api/v1/logout` が送られ、 Cookie が削除される
4. `/login` に遷移する
5. DevTools → **Application** -> **Cookies** で `access_token` が消えていることを確認

### 9.5 認証ガード (proxy)

1. ログイン後の状態で DevTools → **Application** -> **Cookies** -> **http://localhost:3000** から `access_token` を手動で削除
2. http://localhost:3000/ にアクセス
3. `proxy.ts` が Cookie 不在を検知し `/login` にリダイレクト
4. 同じく http://localhost:3000/about にアクセスしても `/login` へリダイレクトされる

---

## まとめ

この章では以下を学びました：

- **`openapi-typescript` で OpenAPI → TypeScript 型生成**: `pnpm gen:api` 1 コマンドで `src/lib/api/schema.ts` が更新される
- **`openapi-fetch` で型安全な fetch クライアント**: `paths` を渡して `apiClient.POST("/api/v1/login", { body })` のように呼ぶと、 backend の Pydantic スキーマと一致した型補完が効く
- **Server / Client 両用の URL 戦略**: `INTERNAL_API_URL`（コンテナ間通信）と `NEXT_PUBLIC_API_URL`（ブラウザから）を環境変数で出し分け、`typeof window === "undefined"` で切り替え
- **`compose.yaml` の `frontend.environment`**: 環境変数の値はここで一元管理。 `NEXT_PUBLIC_` 接頭辞でクライアントバンドル展開される
- **React Hook Form + Zod v4 + Standard Schema**: スキーマ 1 つで「ランタイムバリデーション + TypeScript の型」を両取り。`useForm({ resolver: standardSchemaResolver(schema) })` パターン。Standard Schema 規格経由なので Zod 以外のライブラリにも乗り換えやすい
- **shadcn/ui の `<Field>` 系**: `Field` / `FieldLabel` / `FieldError` / `FieldGroup` などのプリミティブを、React Hook Form の `Controller` と組み合わせて宣言的にフォームを組む。shadcn v4 の base スタイルでは `<Form>` ラッパーは廃止され、`Controller` + `Field` パターンが標準
- **shadcn/ui v4 base-nova は base-ui ベース**: 内部実装が [base-ui](https://base-ui.com/) で、 子要素の差し替えは `asChild` ではなく **`render` プロパティ** を使う (`<DropdownMenuTrigger render={<Button />}>{children}</DropdownMenuTrigger>` のように書く)。 また `DropdownMenuLabel` / `DropdownMenuItem` は **`<DropdownMenuGroup>` の中** に置く必要がある
- **ログインページの実装**: `page.tsx` (Server Component。`metadata` + `<LoginForm />` だけ) と `login-form.tsx` (Client Component。フォーム本体) に **コロケーション** で分割。`'use client'` をフォーム本体に閉じ込め、Server Component のメリットを活かす配置
- **Cookie ベースの認証**: `apiClient.POST("/api/v1/login")` を叩くと backend が `Set-Cookie` で `access_token` を発行。frontend は何も保存せず、以降のリクエストでブラウザが自動送信する
- **Next.js Proxy** (`src/proxy.ts`): Cookie の有無で `/login` にリダイレクト。JWT の中身検証は backend に集約。Next.js 16 で `middleware.ts` から改名され、 runtime も Node.js に変更
- **共通レイアウト** (Route Group で `(public)` と `(authenticated)` に分離): 未ログイン用は `(public)/layout.tsx` にアプリ名のみのシンプルヘッダー。認証下は `(authenticated)/layout.tsx` に shadcn/ui の **Sidebar** (折り畳み可能、 `SidebarMenuButton render={<Link />}` でナビゲーション) + ヘッダー (Sidebar Trigger + アプリ名 + **DropdownMenu + Avatar** のアカウントメニュー) を組み合わせ。 認証側 layout (Server Component) で `GET /api/v1/me` を取得し、 Cookie を `next/headers` の `cookies()` 経由で backend に転送する

これで Cookie ベースの認証フローが一通り動く状態になりました。次の章では、認証済みユーザーが実際の CRUD 画面を操作できるようにしていきます。

## 次の章

[Chapter 12: CRUD 画面の実装 ->](../chapter12/README.md)

Chapter 12 では、Item・User の CRUD 画面を実装します。Server Component で初期データを取得し、Client Component から `TanStack Query` で更新・再取得を扱う構成にしていきます。
