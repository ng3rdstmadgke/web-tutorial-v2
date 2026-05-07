# Chapter 10: Next.js 入門 + Tailwind CSS 基礎

[<- 目次に戻る](../README.md)

## この章のゴール

- `compose.yaml` に `frontend`（Next.js）と **`proxy`（nginx リバースプロキシ）** を追加し、`docker compose up` で起動します
- ブラウザの入口を **nginx に一本化**し、`http://localhost:8080` で Tailwind と shadcn/ui を使ったページが表示されます
- App Router の基本（**ファイルベースルーティング** / **`layout.tsx`** / **Server Component と Client Component** の違い）が分かります
- **Tailwind CSS** のユーティリティクラス・レスポンシブ・バリアント (`hover:`, `focus:`) が使えます
- **shadcn/ui** をセットアップして Button / Card を自分のプロジェクトに取り込めます
- 素の Tailwind を書く場面と shadcn/ui を使う場面の **使い分け** の指針を持てます

## スタート地点

```bash
git checkout chapter10-start
```

## 完成形

```bash
git checkout chapter10-end
```

---

## はじめに

Chapter 8 まででバックエンドの基礎は一通り揃いました。Chapter 9 は外部リンク集だけのお休み章だったので、本格的なフロントエンド実装の最初の一歩はこの Chapter 10 になります。

第 2 部のフロントエンドは **Next.js** + **TypeScript** + **Tailwind CSS** + **shadcn/ui** という組み合わせで進めます。

この章では：

1. Next.js プロジェクトを作る
2. `frontend` サービスを Docker Compose に追加して起動できる状態にする
3. App Router の基本を体験する
4. Tailwind CSS と shadcn/ui をセットアップする

までを行います。バックエンドの API と接続するのは次章以降（Chapter 11 で OpenAPI から TypeScript の型を生成、Chapter 12 でログイン画面を実装）です。

### なぜ Next.js なのか

[Next.js](https://nextjs.org/) は **React ベースのフレームワーク** で、近年 React で Web アプリを作るときの事実上の標準として広く採用されています。素の React だけだとルーティング・データ取得・ビルド・SSR などをすべて自分で組み合わせる必要がありますが、Next.js はこれらを **公式が一式提供** してくれます。

今回は、 Next.js 13以降に導入された **[App Router](https://nextjs.org/docs/app)** というルーティング方式を使用します(推奨)。  
※ App RouterのほかにPage Routerと呼ばれるルーティング方式も存在します。


> [!TIP] 公式ドキュメント:
> - [App Router | Next.js](https://nextjs.org/docs/app)
> - [Server and Client components | Next.js](https://nextjs.org/docs/15/app/api-reference/components/link)
> - [Turbopack | Next.js](https://nextjs.org/docs/app/api-reference/turbopack)

### なぜ Tailwind CSS なのか

[Tailwind CSS](https://tailwindcss.com/) は **utility-first** という思想の CSS フレームワークです。

```html
<!-- 従来の書き方: CSS クラスに意味を持たせて、別ファイルでスタイルを定義 -->
<button class="primary-button">Click me</button>

<!-- Tailwind の書き方: 小さなユーティリティクラスを組み合わせる -->
<button class="bg-blue-500 hover:bg-blue-600 text-white font-bold py-2 px-4 rounded">
  Click me
</button>
```

最初は「クラス名が長い」と感じるかもしれませんが、慣れると：

- **HTML から離れずにスタイルを書けます** … 別の `.css` ファイルを開いたり閉じたりしなくて済みます
- **クラス名を考えなくて済みます** … `.primary-button` のような独自命名を維持する負担がありません
- **未使用 CSS が出ません** … Tailwind は HTML で使われたクラスだけを最終 CSS に含めるので、ファイルサイズが小さく抑えられます

特にチーム開発では、命名規約をめぐる摩擦が減り、デザインの一貫性も保ちやすくなります。

### なぜ shadcn/ui なのか

[shadcn/ui](https://ui.shadcn.com/) は **「ライブラリではなくコピペで使うコンポーネント集」** という、少し変わった立ち位置のツールです。

一般的な UI ライブラリ（MUI、Chakra UI など）は npm パッケージとして依存に追加し、その中のコンポーネントを import して使います。これに対して shadcn/ui は：

```bash
pnpm dlx 'shadcn@^4.7.0' add button
```

を実行すると、**プロジェクトの `src/components/ui/button.tsx` にButton コンポーネントのソースコードがコピーされる** だけです。

メリット：

- **自分のコードとして編集できます** … 「Button にロゴアイコンを足したい」「色を変えたい」のような変更も、ライブラリの仕様に縛られずに書けます
- **Tailwind とネイティブに統合されます** … 別の CSS-in-JS や SCSS が混ざらず、書き方が一貫します
- **依存パッケージが小さくなります** … 使うコンポーネントだけがコピーされるので、バンドルサイズも管理しやすくなります

---

## この章で作るファイル

```
web-tutorial-v2/
├── frontend/                       # <- 今回新規作成
│   ├── package.json
│   ├── pnpm-lock.yaml
│   ├── tsconfig.json
│   ├── next.config.ts              # <- allowedDevOrigins を追記
│   ├── postcss.config.mjs
│   ├── eslint.config.mjs
│   ├── components.json             # shadcn/ui の設定
│   ├── public/
│   └── src/
│       ├── app/
│       │   ├── layout.tsx          # 共通レイアウト (この章で書き換え)
│       │   ├── page.tsx            # トップページ (この章で書き換え)
│       │   ├── globals.css
│       │   └── about/page.tsx      # この章で追加
│       ├── components/
│       │   ├── ui/                 # shadcn/ui のコンポーネント置き場
│       │   │   ├── button.tsx
│       │   │   └── card.tsx
│       │   └── Counter.tsx         # この章で書く Client Component
│       └── lib/utils.ts
├── docker/
│   ├── frontend.Dockerfile         # <- 今回新規作成
│   └── nginx/default.conf          # <- 今回新規作成 (リバースプロキシ設定)
├── compose.yaml                    # <- frontend と proxy サービスを追記
└── .gitignore                      # <- Next.js 系の無視ルールを追記
```

---

## 1. Next.js プロジェクトを作る

Next.js には **公式のセットアップツール** [create-next-app](https://nextjs.org/docs/app/api-reference/create-next-app) があります。これを使うと、TypeScript・Tailwind・ESLint などをセットアップした「動く Next.js プロジェクト」が一発で生成できます。

Dev Container のターミナルで以下を実行します。

```bash
cd $PROJECT_DIR

# Next.js プロジェクトを frontend ディレクトリとして作成
pnpm create next-app@latest frontend \
  --ts \
  --tailwind \
  --eslint \
  --app \
  --use-pnpm \
  --turbopack \
  --src-dir \
  --react-compiler \
  --yes
```

### フラグの意味

| フラグ | 意味 |
|---|---|
| `--ts` | TypeScript を有効化 |
| `--tailwind` | Tailwind CSS (v4) をセットアップ |
| `--eslint` | ESLint を有効化 |
| `--app` | App Router を採用（旧 Pages Router ではない） |
| `--use-pnpm` | パッケージマネージャに pnpm を使う |
| `--turbopack` | 開発サーバー・ビルド共に **[Turbopack](https://nextjs.org/docs/app/api-reference/turbopack)** を採用。Turbopack は Rust 製のバンドラで、従来の Webpack を置き換える Next.js の新しい標準。差分ビルドが非常に速く、ファイル保存からブラウザ反映までの体感が改善する |
| `--src-dir` | `app/` や `components/` を `src/` ディレクトリの下に配置 |
| `--react-compiler` | **[React Compiler](https://nextjs.org/docs/app/api-reference/config/next-config-js/reactCompiler)** を有効化。コンポーネントを自動解析して不要な再レンダリングを抑制してくれるコンパイラで、これまで手で書いていた `useMemo` / `useCallback` / `React.memo` を **書かなくてもパフォーマンスが出る** ようになる。Next.js 16 で安定版が利用可能 |
| `--yes` | 残りの確認をすべてデフォルトで受け入れる |

### 生成されたディレクトリ

```
frontend/
├── src/
│   └── app/
│       ├── favicon.ico
│       ├── globals.css        # Tailwind の import など共通 CSS
│       ├── layout.tsx         # 全ページ共通のレイアウト
│       └── page.tsx           # / (ルート) のページ
├── public/                    # 静的ファイル (画像など)
├── eslint.config.mjs          # ESLint 設定
├── next.config.ts             # Next.js 設定
├── package.json
├── pnpm-lock.yaml
├── postcss.config.mjs         # PostCSS 設定 (Tailwind が利用)
└── tsconfig.json              # TypeScript 設定
```

主要ファイルの役割：

| ファイル | 役割 |
|---|---|
| `src/app/page.tsx` | URL `/` で表示されるページコンポーネント |
| `src/app/layout.tsx` | 全ページ共通の HTML 骨格（`<html>` `<body>` を含む） |
| `src/app/globals.css` | Tailwind の読み込みなど、全ページに共通する CSS |
| `next.config.ts` | Next.js の設定（環境変数の公開、画像最適化など） |
| `tsconfig.json` | TypeScript コンパイラの設定（`@/*` が `src/*` を指すよう設定済み） |
| `postcss.config.mjs` | PostCSS のプラグイン構成（Tailwind v4 が登録されている） |

### pnpm-workspace.yaml を編集

`create-next-app` を実行すると、`frontend/pnpm-workspace.yaml` という小さな設定ファイルが一緒に作られます。デフォルトでは以下のような内容になっています：

```yaml
# frontend/pnpm-workspace.yaml (create-next-app が生成したデフォルト)
ignoredBuiltDependencies:
  - sharp
  - unrs-resolver
```

これは pnpm v10 系で **deprecated** になった書き方なので、以下のように書き換えます。

```yaml
# frontend/pnpm-workspace.yaml
allowBuilds:
  sharp: true
  unrs-resolver: true
```

pnpm v10 以降は **デフォルトでパッケージの postinstall スクリプトを実行しない** ようになっており、`sharp`（画像処理ライブラリ）や `unrs-resolver` のように **ネイティブビルドが必要なパッケージ** はビルド許可を明示的に与える必要があります。  
`--frozen-lockfile` オプション(CI 想定)を付与して `pnpm install` 実行すると、 `[ERR_PNPM_IGNORED_BUILDS]` でインストールに失敗します。

これで「`sharp` と `unrs-resolver` の postinstall スクリプトは安全だと判断したので実行を許可する」という意味になります。

#### 補足: なぜ `allowBuilds` で個別許可なのか?

npm パッケージの postinstall スクリプトは、`pnpm install` 時に **任意のコードを実行できる** 仕組みです。  
間接依存からでも、環境変数（`AWS_ACCESS_KEY` や `GITHUB_TOKEN` など）を抜いたり、`~/.ssh/` の認証情報を読んだり、ファイルを書き換えたりといったことができてしまいます。

実際に過去、複数の **サプライチェーン攻撃** が起きています：

| 事件 | 何が起きたか |
|---|---|
| [`event-stream`](https://blog.npmjs.org/post/180565383195/details-about-the-event-stream-incident) (2018) | 乗っ取られた版で postinstall に Bitcoin ウォレットを盗むコードが仕込まれた |
| [`ua-parser-js`](https://github.com/advisories/GHSA-pjwm-rvh2-c87w) (2021) | 乗っ取られた版が公開され、postinstall でマイナーとパスワード窃取マルウェアが実行された |
| [`node-ipc`](https://github.com/advisories/GHSA-97m3-w2cp-4xx6) (2022) | メンテナが「特定 IP からのインストール時にファイルを破壊する」コードを仕込んだ |

これらの対策として、pnpm 10 から方針が **deny by default**（postinstall はデフォルトで実行しない）に変わりました。`allowBuilds` で「これは信頼している」と明示したパッケージだけが postinstall を実行できるようになっています。

**全許可することも可能** で、`pnpm-workspace.yaml` に以下のように書けばすべての postinstall が無条件に走ります：

```yaml
dangerouslyAllowAllBuilds: true
```

ただし設定名に `dangerously` が付いているとおり、新しく引いた依存（直接でも間接でも）の postinstall がノーチェックで実行されるため、悪意のあるパッケージを引いた瞬間にアウトになります。本チュートリアルは **安全側に倒して個別許可** で進めます。

### .gitignore を更新

`create-next-app` は `frontend/.gitignore` も生成しますが、プロジェクトルートの `.gitignore` には Node 系の除外ルールがまだ書かれていません。ルート側にもまとめておきます。

`.gitignore` の末尾に以下を追記します：

```gitignore
# --- --- --- frontend --- --- ---
.pnpm-store/
node_modules/
.next/
.turbo/
*.tsbuildinfo
frontend/.env*
!frontend/.env.example
```

---

## 2. frontend.Dockerfile を書く

backend と同じく、Next.js もコンテナで動かします。`docker/frontend.Dockerfile` を作成します。

```bash
touch $PROJECT_DIR/docker/frontend.Dockerfile
```

```dockerfile
# docker/frontend.Dockerfile
FROM node:22-bookworm-slim

# pnpm の対話型プロンプトを抑制する
ENV CI=true

# corepack を有効化して pnpm を使えるようにする 
# corepack(https://nodejs.org/api/corepack.html) は Node.js v16.9.0 以降に同梱されているパッケージマネージャ管理ツール
#   - corepack enable: pnpm コマンドを利用可能にする
#   - corepack prepare pnpm@11.1 --activate: pnpm を事前ダウンロード + キャッシュしてデフォルト設定
RUN corepack enable && corepack prepare pnpm@11.1 --activate

WORKDIR /opt/frontend

# 依存定義をコピーしてインストール。 pnpm-workspace.yaml の allowBuilds 設定が
# pnpm install 実行時に有効になるよう、 依存ファイル群と一緒に先にコピーする。
COPY frontend/package.json frontend/pnpm-lock.yaml frontend/pnpm-workspace.yaml ./
# --frozen-lockfile: pnpm-lock.yaml を厳密に守ってインストール (CI でも同じ挙動)
RUN pnpm install --frozen-lockfile

# アプリのソースをコピー
COPY frontend ./

EXPOSE 3000

# 開発サーバーを起動。
# --hostname 0.0.0.0: デフォルトの localhost (127.0.0.1) ではコンテナ外から届かないので 0.0.0.0 で待ち受け
CMD ["pnpm", "dev", "--hostname", "0.0.0.0"]
```

---

## 3. compose.yaml に frontend と proxy を追加

ルートの `compose.yaml` に、**`frontend` (Next.js)** と **`proxy` (nginx リバースプロキシ)** の 2 サービスを追記します。

### なぜリバースプロキシを置くのか

ブラウザの入口を **nginx 1 つに集約**し、パスで振り分けます。

```
browser -> nginx ┬─ /        -> frontend (Next.js)
                 └─ /api/... -> backend  (FastAPI)
```

こうすると、ブラウザから見た **frontend と backend が同一オリジン**（同じ `http://localhost:8080`）になります。これは Chapter 11 以降で重要で、**Cookie 認証が素直に成立**します（別オリジンだと Cookie の共有や CORS で詰まります）。本番でもこの「前段にリバースプロキシ（Ingress）を置いてパスで振り分ける」構成は定番で、Chapter 15 の Kubernetes Ingress とも自然に繋がります。

```yaml
# compose.yaml
services:
  backend:
    # ... 既存の設定（省略） ...

  db:
    # ... 既存の設定（省略） ...

  # ↓↓↓ ここから追加 ↓↓↓
  frontend:
    container_name: web-tutorial-v2-frontend-${HOST_USER}
    build:
      context: .
      dockerfile: docker/frontend.Dockerfile
    volumes:
      # ホットリロード用にホスト側のディレクトリをマウント (ホストの編集が即コンテナに反映される)
      - ${HOST_DIR}/frontend:/opt/frontend
      # node_modules と .next はマウントから除外して、 コンテナ内でインストールされたものを使う
      # (anonymous volume 指定。 仕組みは下の補足参照)
      - /opt/frontend/node_modules
      - /opt/frontend/.next
    networks:
      - devcontainer-nw

  # リバースプロキシ。 ブラウザの唯一の入口になり、 パスで frontend / backend に振り分ける
  proxy:
    container_name: web-tutorial-v2-proxy-${HOST_USER}
    image: nginx:1.27-alpine
    volumes:
      # 振り分け設定 (/ -> frontend, /api/ -> backend)。 次の手順で作成する
      - ${HOST_DIR}/docker/nginx/default.conf:/etc/nginx/conf.d/default.conf:ro
    depends_on:
      - frontend
      - backend
    networks:
      - devcontainer-nw
  # ↑↑↑ ここまで追加 ↑↑↑

networks:
  devcontainer-nw:
    external: true
    name: br-web-tutorial-v2-${HOST_USER}
```

> [!NOTE] ポイント解説:
> - **Docker のパス優先ルール**  
> `volumes` の3つの指定は、Docker の「**同じコンテナ内パスに複数の指定があれば、より深い（具体的な）パスの指定が優先される**」というルールを利用しています。  
> 結果として「`/opt/frontend` 全体はホストと同期するが、その中の `node_modules` と `.next` だけ **穴を開けてホストから切り離す**」状態になります。
>
> | Volume 指定 | コンテナ側のパス | 種類 | 優先度 |
> |---|---|---|---|
> | `${HOST_DIR}/frontend:/opt/frontend` | `/opt/frontend` 全体 | bind mount（ホスト同期） | 低 |
> | `/opt/frontend/node_modules` | `/opt/frontend/node_modules` | anonymous volume | 高 |
> | `/opt/frontend/.next` | `/opt/frontend/.next` | anonymous volume | 高 |
> - **anonymous volume の初期化動作**  
> `host_path:container_path` の形ではなく **container_path だけの volume** は **anonymous volume（匿名ボリューム）** と呼ばれます。  
> 匿名ボリュームには以下の特徴があります:  
>   - **コンテナ初回起動時**: **イメージ内の指定されたパスの中身を匿名ボリュームにコピーして** マウント。
>   - **2 回目以降の起動**: 初回起動時に保存した anonymous volume をマウントします。
>   - **`docker compose down -v`** を実行すると匿名ボリュームも削除されます。
> - **ネットワーク構成**  
>   ```
>   ブラウザ --http://localhost:8080--> proxy(nginx)
>                                         │   /        --> frontend:3000 (Next.js)
>                                         └── /api/... --> backend:8000  (FastAPI) --> db:5432
>
>   ※ frontend / backend / db / proxy はすべて Docker bridge network
>     (br-web-tutorial-v2-${HOST_USER}) 上にあり、 互いにコンテナ名で通信する。
>     ブラウザの入口は proxy (localhost:8080) に一本化される。
>     (proxy:8080 / frontend:3000 / backend:8000 は devcontainer.json の forwardPorts で
>      ローカル環境に転送されるため、 デバッグ時は各コンテナへ直接アクセスもできる)
>   ```

### nginx の設定ファイルを作る

compose で参照している `docker/nginx/default.conf` を作成します。

```bash
mkdir -p $PROJECT_DIR/docker/nginx
touch $PROJECT_DIR/docker/nginx/default.conf
```

```conf
# docker/nginx/default.conf
server {
    listen 8080;
    client_max_body_size 10m;

    # /api/ で始まるパスは backend(FastAPI) へ。
    # proxy_pass に URI を付けないことで、 元のパス(/api/v1/...)をそのまま渡す
    location /api/ {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # それ以外はすべて frontend(Next.js) へ
    location / {
        proxy_pass http://frontend:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Next.js の開発時 HMR(WebSocket) を通す
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

> [!NOTE] ポイント解説:  
> `proxy_pass http://backend:8000;` の `backend` / `frontend` は **compose のサービス名**です。  
> compose は同一ネットワーク上のサービスをサービス名で名前解決できるようにするので、nginx はこの名前でbackend, frontendのコンテナに到達できます。  
> `/api/` を backend、それ以外を frontend に振り分けることで、ブラウザからは 1 つのオリジンに見えます。

### Next.js dev サーバーに proxy オリジンを許可する

Next.js の開発サーバーは、セキュリティのため **起動時のホスト名（既定で `localhost`）以外のオリジン** から開発用リソース（`/_next/*` や HMR）へのアクセスを既定でブロックします。アプリは proxy 経由で配信するので、**proxy のオリジンを許可**しておきます。

`frontend/next.config.ts` に `allowedDevOrigins` を追加します。

```ts
// frontend/next.config.ts
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactCompiler: true,
  // proxy, localhost オリジンに開発用リソース（`/_next/*` や HMR）へのアクセスを許可する
  allowedDevOrigins: ["proxy", "localhost"],
};

export default nextConfig;
```

> [!NOTE] ポイント解説:  
> - **allowedDevOrigins**  
>   開発用リソース（`/_next/*` や HMR）へのアクセスを許可するオリジンのリスト。`allowedDevOrigins` は **開発時のみ** 有効で、本番ビルド（`next build`）には影響しません。  
>   `localhost` はデフォルトで許可だが明示しておく。  
>   `proxy` は **devcontainer内のブラウザ** がアクセスするオリジン

---

## 4. 起動して動作確認

backend と db は Chapter 8 までで既に起動するはずです。frontend と proxy を加えて全体を起動します。

```bash
cd $PROJECT_DIR

# 環境変数 (Chapter 3 で作った .env) を export
export $(grep -v '^#' $PROJECT_DIR/backend/.env | xargs)

# ビルドして起動
docker compose down && docker compose up -d --build

# 起動状態を確認
docker compose ps
# NAME                              SERVICE    STATUS
# web-tutorial-v2-backend-ktamido   backend    Up
# web-tutorial-v2-db-ktamido        db         Up
# web-tutorial-v2-frontend-ktamido  frontend   Up
# web-tutorial-v2-proxy-ktamido     proxy      Up
```

### Next.js デフォルトページの確認

ローカル環境のブラウザで http://localhost:8080 を開きます。create-next-app のデフォルトページ（Next.js のロゴと "Get started" のリンク）が表示されれば成功です。

### ホットリロードの確認

`frontend/src/app/page.tsx` の任意のテキストを書き換えて保存すると、ブラウザが自動でリロードされて変更が反映されます。

---

## 5. App Router の基本

ここからは Next.js の **[App Router | Next.js](https://nextjs.org/docs/app)** を実際に触っていきます。

### 5.1 ページを編集する

`frontend/src/app/page.tsx` を開いて、内容を以下のように丸ごと書き換えます：

```tsx
// frontend/src/app/page.tsx

// ファイル名が `page.tsx` だと、Next.js は コンポーネントを 1 つのページとして扱います
export default function Home() {  // React Component
  return (
    {/* className: React では HTML の `class` 属性ではなく `className` を使います。（class は JS の予約語のため） */}
    <main className="p-8">
      {/* p-8 text-3xl font-bold: Tailwind CSS のユーティリティクラスです。詳しくは次のセクションで解説 */}
      <h1 className="text-3xl font-bold">Hello Next.js</h1>
      <p className="mt-4">これは Next.js の App Router で作った最初のページです。</p>
    </main>
  );
}
```

http://localhost:8080 を再読み込みすると、書き換えた内容が表示されるはずです。


### 5.2 別ページを追加する（ファイルベースルーティング）

App Router では `src/app/` 配下のディレクトリ構造がそのまま URL になります。`src/app/about/page.tsx` を作ると `/about` でアクセスできるページになります。

> [!TIP] 公式ドキュメント:
> - [Layouts and Pages | Next.js](https://nextjs.org/docs/app/getting-started/layouts-and-pages)
> - [Link Component | Next.js](https://nextjs.org/docs/15/app/api-reference/components/link)

```bash
mkdir -p $PROJECT_DIR/frontend/src/app/about
touch $PROJECT_DIR/frontend/src/app/about/page.tsx
```

```tsx
// frontend/src/app/about/page.tsx
export default function AboutPage() {
  return (
    <main className="p-8">
      <h1 className="text-3xl font-bold">About</h1>
      <p className="mt-4">このアプリは Web チュートリアル v2 のサンプルです。</p>
    </main>
  );
}
```

http://localhost:8080/about にアクセスすると About ページが表示されます。

### ファイルベースルーティングの規則

| ファイル | URL |
|---|---|
| `src/app/page.tsx` | `/` |
| `src/app/about/page.tsx` | `/about` |
| `src/app/items/page.tsx` | `/items` |
| `src/app/items/[id]/page.tsx` | `/items/123`（`[id]` は[動的パラメータ](https://nextjs.org/docs/app/api-reference/file-conventions/dynamic-routes)） |
| `src/app/items/[id]/edit/page.tsx` | `/items/123/edit` |

ディレクトリを作ってその中に `page.tsx` を置くだけで新しいルートが増える、というのが App Router の中心的な仕組みです。

### 5.3 ページ間のリンク

ページ間の遷移には Next.js が提供する [`<Link>`](https://nextjs.org/docs/app/getting-started/linking-and-navigating) コンポーネントを使います。`src/app/page.tsx` を以下のように書き換えます：

```tsx
// frontend/src/app/page.tsx
import Link from "next/link";

export default function Home() {
  return (
    <main className="p-8">
      <h1 className="text-3xl font-bold">Hello Next.js</h1>
      <p className="mt-4">これは Next.js の App Router で作った最初のページです。</p>
      <p className="mt-4">
        <Link href="/about" className="text-blue-500 underline">
          About ページへ
        </Link>
      </p>
    </main>
  );
}
```

「About ページへ」のリンクをクリックすると `/about` に遷移します。

> **`<a>` ではなく `<Link>` を使う理由**
> `<a href="/about">` でも遷移はできますが、その場合は **ブラウザが全ページをフルリロード** します。`<Link>` を使うと Next.js が **必要な部分だけを非同期に取得** して画面を切り替えるので、ページ遷移が高速になります（SPA 的な体験）。

### 5.4 共通レイアウト

`src/app/layout.tsx` は **全ページに共通するレイアウト** を定義する場所です。ヘッダーやフッターのように、どのページでも表示したい部分はここに書きます。

> [!TIP] 公式ドキュメント:
> - [Layouts and Pages - Creating a layout | Next.js](https://nextjs.org/docs/app/getting-started/layouts-and-pages#creating-a-layout)

```tsx
// frontend/src/app/layout.tsx
import Link from "next/link";
import type { Metadata } from "next";
import "./globals.css";

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
    <html lang="ja">
      <body>
        <header className="border-b p-4">
          <nav className="flex gap-4">
            <Link href="/" className="font-bold">Home</Link>
            <Link href="/about">About</Link>
          </nav>
        </header>
        {/* children: 各ページ (`page.tsx`) がここに差し込まれます */}
        {children}
      </body>
    </html>
  );
}
```

`/` でも `/about` でも、画面の上端に Home / About のナビゲーションが表示されるようになります。

> [!NOTE] ポイント解説:
> - **[`metadata`](https://nextjs.org/docs/app/getting-started/metadata-and-og-images)** … ブラウザのタブに表示されるタイトルや、SEO 用の meta タグを設定できます


### 5.5 Server Component と Client Component

Next.jsには **Server Component** と **Client Component** という概念が存在します。  

> **Server Component & Client Component**  
> - [Server and Client Component | Next.js](https://nextjs.org/docs/app/getting-started/server-and-client-components)
> - [use client | Next.js](https://nextjs.org/docs/app/api-reference/directives/use-client)


- **Server Component**  
  **サーバー側** でデータの取得やレンダリングを行い、その結果をクライアントに送信します。ブラウザ側でのデータ取得やレンダリングが発生しないため、表示が高速でSEO に強いのが特徴です。
- **Client Component**  
**クライアント(ブラウザ)側** で実行され、ブラウザAPI(window, localstorage)や[React Hooks](https://react.dev/reference/react/hooks)、イベントハンドラ( `onClick` など)を利用できます。 ボタンクリックで値を変えたり、フォーム入力に応じて画面を切り替えたりといった **ユーザー操作に応答する UI** を作るときに使います。

ちなみに、ここまで書いてきたコンポーネントはすべて **Server Component** です。

App Router では **Server Component がデフォルト** で、Client Component にしたいファイルだけ先頭に `"use client"` という宣言を 1 行加えます。  
**まず Server Component で書いてみて、必要になったときだけ Client Component に切り替える** のが推奨パターンです。これによりブラウザに送る JavaScript の量を最小化できます。


> **`@/components/Counter` の `@/` とは?**
> `@/...` は `tsconfig.json` で設定された **絶対パスのエイリアス** で、プロジェクトルートを指します。`../../components/Counter` のような相対パスを書かなくて済むので、ディレクトリの階層が変わってもパスを直さずに済みます。


> **React hooks とは?**  
> Hooks は React 関数コンポーネントの中で **状態 (`useState`)** や **副作用 (`useEffect`)** などを扱うための仕組みで、慣習として `use` で始まる名前を持ちます。例えば `useState` はコンポーネントが内部に **書き換え可能な値（state）** を持てるようにする hook で、`onClick` などのイベントで値を更新するとコンポーネントが自動で再描画されます。
> - [Built-in React Hooks | React.js](https://react.dev/reference/react/hooks)
>   - [useState - hooks | React.js](https://react.dev/reference/react/useState)
>   - [useEffect - hooks | React.js](https://react.dev/reference/react/useEffect)



#### Server / Client の使い分け方針

| やりたいこと | どちら？ |
|---|---|
| 静的なテキスト・レイアウトを表示する | Server Component |
| サーバー側で DB / API からデータを取得する | Server Component |
| [React Hooks](https://react.dev/reference/react/hooks) を使う | Client Component |
| ボタンクリック・フォーム入力など、ユーザー操作を扱う | Client Component |
| `localStorage`, `window.location` などのブラウザを使う| Client Component |


#### Client コンポーネントを実装してみる

例として、ボタンを押すとカウントが増える Counter コンポーネントを Client Component で作ります。

```bash
mkdir -p $PROJECT_DIR/frontend/src/components
touch $PROJECT_DIR/frontend/src/components/Counter.tsx
```

```tsx
// frontend/src/components/Counter.tsx
"use client";

import { useState } from "react";

export function Counter() {
  const [count, setCount] = useState(0);
  return (
    <div className="flex items-center gap-4">
      <button
        onClick={() => setCount(count + 1)}
        className="bg-blue-500 hover:bg-blue-600 text-white font-bold py-2 px-4 rounded"
      >
        +1
      </button>
      <span>count: {count}</span>
    </div>
  );
}
```

`src/app/page.tsx` に組み込みます：

```tsx
// frontend/src/app/page.tsx
import Link from "next/link";
import { Counter } from "@/components/Counter";

export default function Home() {
  return (
    <main className="p-8">
      <h1 className="text-3xl font-bold">Hello Next.js</h1>
      <p className="mt-4">これは Next.js の App Router で作った最初のページです。</p>
      <p className="mt-4">
        <Link href="/about" className="text-blue-500 underline">
          About ページへ
        </Link>
      </p>
      {/* 追加 --> */}
      <div className="mt-8">
        <Counter />
      </div>
      {/* <-- 追加 */}
    </main>
  );
}
```

ボタンをクリックするとカウントが増えるはずです。**ボタンの `onClick` を成立させるために、Counter は Client Component になっている** ことに注目してください。

---

## 6. Tailwind CSS の基本

- [Tailwind CSS](https://tailwindcss.com/)

ここまで何気なく `className="p-8"` のような Tailwind のクラスを書いてきました。改めて Tailwind の使い方を整理します。

### 6.1 ユーティリティクラス

- [Styling with utility classes | Tailwind CSS](https://tailwindcss.com/docs/styling-with-utility-classes)

Tailwind では、**1 クラス = 1 つの CSS ルール** が原則です。

| クラス | 対応する CSS | 役割 |
|---|---|---|
| `p-8` | `padding: 2rem;` | 内側余白 |
| `m-4` | `margin: 1rem;` | 外側余白 |
| `text-3xl` | `font-size: 1.875rem;` | フォントサイズ |
| `font-bold` | `font-weight: 700;` | 太字 |
| `bg-blue-500` | `background-color: oklch(0.623 0.214 259.815);` | 背景色 |
| `text-white` | `color: #fff;` | 文字色 |
| `rounded` | `border-radius: 0.25rem;` | 角丸 |
| `flex` | `display: flex;` | フレックスコンテナ |
| `gap-4` | `gap: 1rem;` | アイテム間スペース |
| `border-b` | `border-bottom-width: 1px;` | 下線（枠線） |

数値は基本的に **`4` を 1 単位 = 1rem** とした 0.25rem 刻みです。`p-1` は 0.25rem、`p-4` は 1rem、`p-8` は 2rem になります。

> **すべてのクラスを覚える必要はない**
> Tailwind のクラスは膨大にありますが、すべて覚える必要はありません。エディタの拡張機能（VS Code なら [Tailwind CSS IntelliSense](https://marketplace.visualstudio.com/items?itemName=bradlc.vscode-tailwindcss)）を入れると、`bg-` まで打った時点で候補が出てくるので、必要なクラスを見つけながら書けます。

### 6.2 レスポンシブ

- [Responsive Design | Tailwind CSS](https://tailwindcss.com/docs/responsive-design)

画面幅に応じてスタイルを切り替えるには **ブレークポイントプレフィックス** を付けます。

| プレフィックス | 適用される画面幅 |
|---|---|
| なし | すべて（モバイル含む） |
| `sm:` | 640px 以上 |
| `md:` | 768px 以上 |
| `lg:` | 1024px 以上 |
| `xl:` | 1280px 以上 |

例：

```tsx
<div className="p-4 md:p-8 lg:p-16">
  {/* モバイル: p-4 / タブレット: p-8 / デスクトップ: p-16 */}
  Hello
</div>
```

Tailwind は **モバイルファースト** の設計です。プレフィックスのないクラスは「すべての画面サイズ」に適用され、`md:` 以降のクラスはそれぞれ「画面幅が xx 以上」のときに上書きします。

### 6.3 状態 (hover / focus)

- [Hover, forcus, and other states | Tailwind CSS](https://tailwindcss.com/docs/hover-focus-and-other-states)

要素の状態に応じてスタイルを切り替えるには **状態プレフィックス** を付けます。

| プレフィックス | 適用されるとき |
|---|---|
| `hover:` | マウスホバー時 |
| `focus:` | フォーカス時（クリック後、Tab で選択時） |
| `active:` | クリック中 |
| `disabled:` | 無効化された input/button |

例：

```tsx
<button class="bg-blue-500 hover:bg-blue-600 focus:ring-2 focus:ring-blue-300">
  Click
</button>
```

通常時は `bg-blue-500`、ホバーで `bg-blue-600` に切り替わり、フォーカス時は青色のリングが表示されます。


### 6.4 ダークモード

- [Dark mode | Tailwind CSS](https://tailwindcss.com/docs/dark-mode)

Tailwind では **`dark:` バリアント** を付けたクラスが、ダークモード時にだけ適用されます。

```html
<div class="bg-white text-black dark:bg-zinc-900 dark:text-white">
  ライト時は白背景・黒文字、ダーク時は濃いグレー背景・白文字
</div>
```

「ダークモードかどうか」をどう判定するかは **2 通り** あります。

| 戦略 | 判定方法 | 主な用途 |
|---|---|---|
| **`prefers-color-scheme`**（デフォルト）| OS / ブラウザのダークモード設定に追従 | ユーザー操作なしで自動切り替え。最も簡単 |
| **クラス制御** | `<html class="dark">` のように DOM のクラスで切り替える | ユーザーがボタンで明示的に切り替えるパターン |

`create-next-app` が生成する `globals.css` は **OS 追従** が初期状態で設定されています（実装は 6.6 で見ます）。本チュートリアルでは OS 追従のままで進めます。

> ユーザーがボタンでテーマをトグルするパターン（`<html>` に `dark` クラスを付け外しする実装）は、状態管理が絡むので Chapter 12 以降のクライアント実装で扱います。

### 6.5 カラー

- [Colors | Tailwind CSS](https://tailwindcss.com/docs/colors)

Tailwind には **組み込みのカラーパレット** があり、`色名-濃度` の形でユーティリティクラスとして使えます。

```html
<div class="bg-blue-500 text-white">青背景・白文字</div>
<div class="bg-zinc-100 text-zinc-900">薄いグレー背景・濃いグレー文字</div>
```

- **色名**: `slate`、`gray`、`zinc`、`neutral`、`stone`、`red`、`orange`、`amber`、`yellow`、`lime`、`green`、`emerald`、`teal`、`cyan`、`sky`、`blue`、`indigo`、`violet`、`purple`、`fuchsia`、`pink`、`rose` の 22 色
- **濃度**: `50`、`100`、`200`、… `900`、`950`（数字が大きいほど濃い）
- どんなプロパティでも使えます: `bg-blue-500`（背景）、`text-blue-500`（文字色）、`border-blue-500`（枠線色）、`ring-blue-500`（フォーカスリング）など

#### 透過度

色名の後ろに `/数値` を付けると **不透明度** を指定できます。

```html
<div class="bg-blue-500/50">不透明度 50% の青背景</div>
<div class="bg-blue-500/25">不透明度 25% の青背景</div>
```


### 6.6 globals.css でカスタマイズ

Tailwind CSS v4 では、**CSS ファイルの中で直接、テーマや独自ユーティリティの設定を書く** スタイルが推奨されています。その入口になるのが、`create-next-app` が生成した `src/app/globals.css` です。

#### 初期状態

`src/app/globals.css` を開くと、以下のような内容になっています：

```css
/* frontend/src/app/globals.css */
@import "tailwindcss";

:root {
  --background: #ffffff;
  --foreground: #171717;
}

@theme inline {
  --color-background: var(--background);
  --color-foreground: var(--foreground);
  --font-sans: var(--font-geist-sans);
  --font-mono: var(--font-geist-mono);
}

@media (prefers-color-scheme: dark) {
  :root {
    --background: #0a0a0a;
    --foreground: #ededed;
  }
}

body {
  background: var(--background);
  color: var(--foreground);
  font-family: Arial, Helvetica, sans-serif;
}
```

それぞれの構文の役割を順に見ていきます。

#### `@import "tailwindcss"`

Tailwind 本体（プリセット・基本リセット・ユーティリティ生成エンジン）を読み込みます。

##### Preflight — ブラウザ間のスタイルを揃える base reset

`@import "tailwindcss"` には Tailwind 独自の CSS リセット **[Preflight](https://tailwindcss.com/docs/preflight)** が含まれます。  
これは Tailwind が提供する **「ブラウザ間のデフォルトスタイルを統一するための base style 群」** で、Tailwind を使う前提条件として設計されています。ベースは [modern-normalize](https://github.com/sindresorhus/modern-normalize) です。

代表的なリセット内容：

| 元のブラウザ挙動 | Preflight 適用後 |
|---|---|
| `<h1>`〜`<h6>` は大きな太字 + マージン | サイズも太字もなくなり、`<p>` と同じ見た目になる（→ Tailwind ユーティリティで都度指定する前提） |
| `<ul>` `<ol>` に箇条書きマーカー | マーカーが消える |
| `<button>` にブラウザ独自のグレー背景・枠線 | プレーンに（自分で `bg-*` / `border-*` を当てる前提） |
| 画像が `inline` で text-baseline に揃う | `display: block` で扱いやすく |
| `<body>` のデフォルトフォントはブラウザ依存 | **`font-family: var(--font-sans)`** が自動で当たる |
| `<code>` `<pre>` `<kbd>` `<samp>` のフォントはブラウザ依存 | **`font-family: var(--font-mono)`** が自動で当たる |
| 要素の `border-color` はブラウザ依存（黒など） | 全要素 `currentColor`（文字色と同じ）になる |

最後の 2 行が、後の 6.7 で `<body>` や `<code>` にフォントを自動で当てるための仕組みになっています。

> **Preflight は `@layer base` で読み込まれるので、自分が書いたスタイルが優先される**  
> Preflight は CSS の `@layer base { ... }` の中で読み込まれます。CSS の **cascade layer** の仕組みにより、`@layer` の外で書いた通常のセレクタ（例えば `globals.css` の `body { ... }`）は **Preflight より優先** されます。


#### `:root { ... }` で CSS 変数を定義

`:root` セレクタは **HTML 全体に効く CSS 変数（カスタムプロパティ）** を定義する場所です。`--background` `--foreground` のように `--` で始まる名前は CSS 変数で、`var(--background)` という構文で参照できます。

ここで定義した変数を後段の `@theme inline` から参照することで、「テーマ変数の中身を後で差し替えられる」設計になっています（ダークモード切り替えで活用）。

#### `@theme inline { ... }` でテーマを定義

- [Theme variables | Tailwind CSS](https://tailwindcss.com/docs/theme)

**Tailwind v4 で最も重要なディレクティブ** です。`@theme` ブロックの中で定義した変数は、**対応するユーティリティクラスが自動生成されます**。

| `@theme` 内の変数 | 自動生成されるユーティリティ |
|---|---|
| `--color-background: var(--background);` | `bg-background`、`text-background`、`border-background` ... |
| `--color-primary: oklch(0.5 0.2 250);` | `bg-primary`、`text-primary` ... |
| `--font-sans: var(--font-geist-sans);` | `font-sans` |
| `--font-mono: var(--font-geist-mono);` | `font-mono` |
| `--spacing-72: 18rem;` | `p-72`、`m-72`、`gap-72` ... |

`inline` キーワードを付けると、`var(--background)` のような **参照値** がビルド時に展開されずそのまま `var(...)` として残ります。これにより、後から `:root` 側の値を書き換えるだけでテーマがすぐ切り替わります（次のダークモード対応がこの仕組みで成立）。


**フォントの設定** もここで行います。Next.js の [next/font](https://nextjs.org/docs/app/getting-started/fonts) で読み込んだ Geist Sans / Mono を `--font-geist-sans` / `--font-geist-mono` という CSS 変数として `<body>` に注入し、それを `--font-sans` / `--font-mono` 経由で Tailwind の `font-sans` / `font-mono` クラスに繋いでいます。

#### `@media (prefers-color-scheme: dark)` でダークモード切り替え

```css
@media (prefers-color-scheme: dark) {
  :root {
    --background: #0a0a0a;
    --foreground: #ededed;
  }
}
```

OS のダークモード設定が ON のときだけ `:root` の `--background` / `--foreground` の値を **上書き** します。`@theme inline` が `var(--background)` で参照しているので、ユーティリティクラス側（`bg-background` など）も自動でダーク色に切り替わります。**CSS だけでダークモード対応が完結する** のがポイントです。

#### `body { ... }` で通常 CSS も書ける

`globals.css` は普通の CSS ファイルでもあるので、`body` セレクタや独自クラスなど、Tailwind を介さない通常の CSS もそのまま書けます。

#### `@utility` で独自のユーティリティを足す

- [Functions and directives - `@utility` | Tailwind CSS](https://tailwindcss.com/docs/functions-and-directives#utility-directive)

Tailwind には数百のユーティリティが標準で用意されていますが、次のような場面では足りなくなります：

- Tailwind が提供していない CSS プロパティを使いたい（例: `content-visibility`、`mask-image`）
- プロジェクト独自のスタイル組み合わせを 1 クラスにまとめて再利用したい

このときに使うのが **`@utility`** ディレクティブです。例として「`content-visibility: auto;` を当てるユーティリティ `content-auto` を作る」場合：

```css
@utility content-auto {
  content-visibility: auto;
}
```

これで HTML 側から `class="content-auto"` と書けます。Tailwind 標準のユーティリティと同じ扱いなので、`md:content-auto`（768px 以上で適用）や `hover:content-auto`（ホバー時に適用）のような **バリアントを付けた書き方も自動で使えるようになります**。

## 7. shadcn/ui のセットアップ

- [shadcn/ui](https://ui.shadcn.com/)

UI コンポーネント（ボタン、カード、モーダルなど）は自前で作ってもいいのですが、毎回ゼロから作るのは大変です。shadcn/ui が用意している **コピペで使えるコンポーネント集** を導入します。

### 7.1 init で初期化

`frontend/` ディレクトリで `shadcn` の init コマンドを実行します。

```bash
cd $PROJECT_DIR/frontend

# shadcn/ui をデフォルト構成で初期化
pnpm dlx 'shadcn@^4.7.0' init --defaults --yes
```

### フラグの意味

| フラグ | 意味 |
|---|---|
| `--defaults` | デフォルト構成（`template=next`、`preset=base-nova`）で初期化します。プリセットには **Button コンポーネント** と **テーマ用フォント**（Geist Sans / Mono）の追加までが含まれます |
| `--yes` | 確認プロンプトをすべてデフォルトで受け入れます |

実行後、以下のファイル・ディレクトリが生成 / 更新されます：

| パス | 役割 |
|---|---|
| `components.json` | shadcn/ui の設定ファイル（コンポーネントの配置先・スタイル） |
| `src/components/ui/button.tsx` | shadcn/ui の **Button コンポーネント**（init 時に自動配置） |
| `src/lib/utils.ts` | クラス名の結合などに使う `cn()` ユーティリティ関数 |
| `src/app/globals.css` | shadcn/ui のテーマ変数（カラー・ボーダー半径など）が追記される |
| `src/app/layout.tsx` | Geist Sans / Mono フォントを読み込むよう更新される |

依存パッケージとして `@base-ui/react`、`class-variance-authority`、`clsx`、`lucide-react`、`tailwind-merge`、`tw-animate-css` などが追加されます。

### `pnpm-workspace.yaml` の `allowBuilds` に `msw` を追記

shadcn が依存として取り込むパッケージの中に、postinstall スクリプトを持つ [`msw`](https://mswjs.io/)（テスト用のモックサービスワーカー）が含まれています。Section 1 で書いた `pnpm-workspace.yaml` には `msw` の許可がまだ無いため、次回 `docker compose build` 時に `[ERR_PNPM_IGNORED_BUILDS] Ignored build scripts: msw@...` で失敗します。

`frontend/pnpm-workspace.yaml` に `msw` の行を追加します：

```yaml
# frontend/pnpm-workspace.yaml
allowBuilds:
  msw: true            # <- 追加
  sharp: true
  unrs-resolver: true
```

これで Docker イメージのリビルドが通るようになります。

> **なぜ shadcn が `msw` を引いてくるのか?**
> shadcn 4 の `base-nova` プリセットには、コンポーネントを単独でデモ・テストできる仕組みが含まれており、その依存として `msw`（モック HTTP の差し込み）も入ります。本チュートリアルでは `msw` を能動的には使いませんが、`pnpm install` で警告を出させないために許可しておきます。

### 7.2 アプリを再起動

```bash
cd $PROJECT_DIR

# 環境変数 (Chapter 3 で作った .env) を export
export $(grep -v '^#' $PROJECT_DIR/backend/.env | xargs)

# ビルドして起動
docker compose down && docker compose up -d --build
```

### 7.3 Button を使ってみる

`--defaults` で初期化したことで、Button コンポーネント (`src/components/ui/button.tsx`) は **既に配置済み** です。中身を覗いてみてください — **これは npm パッケージから取り込まれたコードではなく、自分のプロジェクトのソースとして配置された** Button コンポーネントです。読めますし、編集もできます。

### 使ってみる

`src/app/page.tsx` を以下のように書き換えます：

```tsx
// frontend/src/app/page.tsx
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
    </main>
  );
}
```

ページを再読み込みすると、5 種類のスタイルのボタンが並んで表示されます。

### 7.4 Card を追加する

Card は init には含まれていないので、`shadcn add` で追加します。

```bash
pnpm dlx 'shadcn@^4.7.0' add card --yes
```

About ページを Card で装飾してみます。`src/app/about/page.tsx` を以下のように書き換えます：

```tsx
// frontend/src/app/about/page.tsx
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
```

http://localhost:8080/about を開くと、整ったカード形式で About 情報が表示されます。

> **shadcn/ui のコンポーネントは「自分のコード」**
> `src/components/ui/button.tsx` や `card.tsx` は **コピーされた後は完全に自分のもの** です。「Card の枠線をもっと太くしたい」「Button にスピナーを足したい」のような変更は、このファイルを直接書き換えれば OK。npm の更新を待つ必要も、ライブラリの API に縛られることもありません。

---

## 8. Google Fonts を導入する

- [font-family | Tailwind CSS](https://tailwindcss.com/docs/font-family)

実務では [Google Fonts](https://fonts.google.com/) のような外部フォントを使う場面が頻出します。Next.js には公式の **[next/font/google](https://nextjs.org/docs/app/api-reference/components/font)** があり、ビルド時にフォントを取得してプロジェクト内に同梱してくれます。

このアプローチには以下のメリットがあります：

- **実行時に Google にアクセスしません** … ビルド時にフォントファイルをプロジェクト内に取り込むので、ユーザーがページを開いたときに Google のサーバーを経由しません（プライバシー保護・速度改善）
- **CLS (Cumulative Layout Shift) 対策が自動** … フォント読み込み中のレイアウトずれを抑制してくれます
- **Tailwind v4 の `@theme inline` と相性が良い** … `variable` プロパティで CSS 変数として注入できるので、6.6 で見た Tailwind のテーマ変数に直接繋がります

例として、英数字に **Inter**、日本語に **Noto Sans JP** を使う一般的な構成を組んでみます。

### 8.1 sans-serif と monospace の使い分け

その前に、Web で扱うフォントは大きく **2 種類** あることを押さえておきます。

| 種類 | 特徴 | 主な用途 | 例 |
|---|---|---|---|
| **sans-serif（可変幅）** | 文字ごとに幅が違う（`i` は狭く `W` は広い）。文章として読みやすい | 通常の本文・見出し・UI ラベル | Inter、Noto Sans JP、Roboto |
| **monospace（等幅）** | すべての文字が同じ幅。縦の桁が揃う | **コード表示**（インデント・桁揃いが重要）、技術的な値 | Geist Mono、JetBrains Mono、Fira Code |

ブラウザは `<code>` `<pre>` `<kbd>` などの要素にデフォルトで等幅フォントを当てます。Tailwind 側にも、通常テキスト用の **`font-sans`** クラスと、コード表示用の **`font-mono`** クラスが用意されていて、それぞれ `--font-sans` / `--font-mono` のテーマ変数が値を決めています。だから「**通常テキスト用の sans**」と「**コード用の mono**」の両方をフォントとして設定するのが定石です。

### 8.2 layout.tsx でフォントを読み込む

`src/app/layout.tsx` を以下のように書き換えます（既存の Geist Sans を Inter + Noto Sans JP に置き換え、等幅フォントの Geist Mono は据え置き）：

```tsx
// frontend/src/app/layout.tsx
import type { Metadata } from "next";
import { Inter, Noto_Sans_JP, Geist_Mono } from "next/font/google";  // <- 追加
import "./globals.css";

/* 追加 -->*/
// Inter: 英数字用の sans-serif。 <body> 全体や見出しなど通常テキスト用。
// Inter({ subsets, variable }) の戻り値は、 指定した CSS 変数 (--font-inter) を
// 有効化するためのクラス名とフォント設定を一括で扱う Wrapper。
// subsets: ["latin"] = 取り込むサブセット (latin は基本ラテン文字)
const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
});

// Noto_Sans_JP: 日本語用の sans-serif。 Inter は日本語グリフを持たないので組み合わせる。
// 日本語グリフはフォントファイル本体に含まれているので subsets: ["latin"] だけで OK
const notoSansJP = Noto_Sans_JP({
  subsets: ["latin"],
  variable: "--font-noto-sans-jp",
});

// Geist_Mono: コード表示用の monospace。 <code> や <pre> で使われる
const geistMono = Geist_Mono({
  subsets: ["latin"],
  variable: "--font-geist-mono",
});
/* <-- 追加 */

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
    // 各フォントの .variable は「CSS 変数を有効化するクラス名」を返す。
    // テンプレートリテラルで連結して <html> に渡すと 3 つの CSS 変数が同時に有効になる
    <html
      lang="ja"
      className={`${inter.variable} ${notoSansJP.variable} ${geistMono.variable}`}
    >
      {/* ... */}
    </html>
  );
}
```

> [!TIP] 別のフォントを使いたいときは、`next/font/google` の import を差し替えるだけで切り替えられます。フォント名は [Google Fonts のサイト](https://fonts.google.com/) で探して、スペースをアンダースコアに置き換えれば API 名になります（例: `Source Sans 3` -> `Source_Sans_3`）。


### 8.3 globals.css で Tailwind のデフォルトフォントに紐付ける

shadcn init で書き換わった `src/app/globals.css` の `@theme inline` ブロックの、`--font-sans: ...`を Inter + Noto Sans JP の優先スタックに書き換えます。

```css
/* src/app/globals.css */

@theme inline {
  /* ... shadcn が書き込んだ他のテーマ変数 (--color-card 等) ... */

  /* --font-sans: 通常テキスト用 (font-sans クラスや <body> 直下) で使われるフォント。
     CSS の font-family は左から順にフォントを試す仕組みなので、
     英数字 = Inter、 Inter にグリフが無い日本語 = Noto Sans JP で表示される。
     末尾の sans-serif はどちらも読み込めなかった場合の最終フォールバック */
  --font-sans: var(--font-inter), var(--font-noto-sans-jp), sans-serif;  /* <- var(--font-sans) から書き換え */

  /* --font-mono は shadcn init が設定済みなので触らない (コード表示用フォント) */
  --font-mono: var(--font-geist-mono);
  /* ... 以下、他のテーマ変数 ... */
}
```

### 8.4 動作確認

### sans フォント（本文）の確認

アプリ全体の文字が新しいフォント（英数字 = Inter、日本語 = Noto Sans JP）で表示されます。  
ブラウザの DevTools の Elements タブで `<body>` の Computed `font-family` を確認すると、`var(--font-inter), var(--font-noto-sans-jp), sans-serif` の順に展開されているのが見えます。

### mono フォント（コードブロック）の確認

`<code>` `<pre>` `<kbd>` `<samp>` といった **コード関連の HTML 要素** には、 `--font-mono` があたります。(Tailwind v4 の preflight が `font-family: var(--font-mono, ...)` を当てる仕様になっているため)

確認のため、`src/app/page.tsx` に一行追加してみます：

```tsx
// src/app/page.tsx

// ...

export default function Home() {
  return (
    <main className="p-8">
      {/* ... */}
      <p className="mt-4">変数 <code>let foo = 1;</code> はインライン要素として Geist Mono が当たります</p>
    </main>
  );
}
```

ブラウザでリロードして `<code>` 部分を見ると、**周りの本文（Inter）と書体が異なり、文字幅が揃った等幅フォント** で表示されます。DevTools の Elements タブで `<code>` を選択し、Computed の `font-family` を確認すると `"Geist Mono", "Geist Mono Fallback"` になっています。

任意の要素にも `className="font-mono"` を付ければ Geist Mono を当てられます：

```tsx
// src/app/page.tsx

// ...

export default function Home() {
  return (
    <main className="p-8">
      {/* ... */}
      <div className="font-mono">この div も Geist Mono が当たります</div>
    </main>
  );
}
```

---

## 9. Tailwind と shadcn/ui の使い分け

| ケース | Tailwind 素書き | shadcn/ui |
|---|---|---|
| 余白・色の微調整 | ✅ | （Tailwind を併用） |
| レイアウト (flex, grid) | ✅ | — |
| ボタン・カード・モーダル・フォームのような **UI 部品** | △ （自前で作ると大変） | ✅ |
| その UI 部品を何回も使う / アプリ全体で見た目を統一したい | △ | ✅ |
| 1 ページだけのカスタムレイアウト | ✅ | — |

ざっくり言うと：

- **「ありがちな UI 部品」が必要 -> shadcn/ui で追加します**（Button、Card、Dialog、Form、Tabs、Table など）
- **「部品を並べる、余白を取る、色を変える」 -> Tailwind を素で書きます**

例えば「Card の中に Tailwind でレイアウトを組んで、Button を 2 つ並べる」のような書き方が頻出パターンです。Tailwind と shadcn/ui は競合せず、**併用** が前提です。

---

## まとめ

この章では以下を学びました：

- **Next.js プロジェクトの作成**: `pnpm create next-app` をフラグ指定で実行しました（対話プロンプトに頼らず、`--ts` / `--tailwind` / `--app` / `--use-pnpm` / `--turbopack` / `--src-dir` / `--react-compiler` を一括指定）
- **pnpm-workspace.yaml の `allowBuilds`**: `sharp` / `unrs-resolver` のような postinstall を伴うパッケージは pnpm v10 以降は明示許可が必要。背景にあるサプライチェーン攻撃の文脈と、`dangerouslyAllowAllBuilds` ではなく個別許可を選ぶ理由も押さえました
- **frontend.Dockerfile**: `node:22-bookworm-slim` + corepack で pnpm をマイナー固定、`ENV CI=true` で Next.js 起動時の依存チェックの TTY 待ちを回避
- **compose.yaml に frontend サービス追加**: bind mount + anonymous volume で `node_modules` / `.next` を「ホスト OS のディレクトリから穴あけして切り離す」テクニック、Docker のパス優先ルール、コンテナ間通信時はホスト名がコンテナ名になることを学びました
- **App Router の基本**: ファイルベースルーティング、`src/app/page.tsx` / `src/app/layout.tsx` / `<Link>`、Server Component / Client Component の違いと `"use client"` の使いどころ
- **Tailwind CSS**: ユーティリティクラス・レスポンシブ (`md:`, `lg:`)・バリアント (`hover:`, `focus:`)・ダークモード (`dark:` バリアント + `prefers-color-scheme` で OS 追従)・カラー (`bg-color-shade` + 透過度 + 任意値)、Tailwind v4 の `@import "tailwindcss"` / Preflight / `@theme inline` / `@utility` の役割
- **shadcn/ui**: `shadcn init --defaults` で `components.json` / Button / フォント / テーマを一括セットアップし、`shadcn add card` でコンポーネントを足す流れ。`src/components/ui/` に **自分のコードとして** 配置される shadcn/ui の思想を体験
- **Google Fonts の導入**: `next/font/google` で Inter + Noto Sans JP + Geist Mono を CSS 変数として注入し、`globals.css` の `@theme inline { --font-sans: ... }` 1 行で sans / mono / heading を一括差し替え
- **Tailwind と shadcn/ui の使い分け**: UI 部品 (Button、Card、Dialog、Form 等) は shadcn/ui、レイアウトや微調整は Tailwind。両者は **競合せず併用** が前提

これで `docker compose up` するだけで **backend (FastAPI) + db (PostgreSQL) + frontend (Next.js)** の 3 サービスが揃い、Tailwind と shadcn/ui で UI を組める状態になりました。

## 次の章

[Chapter 11: OpenAPI 駆動の型生成 ->](../chapter11/README.md)

Chapter 10 では frontend を「動かす」ところまでで止めました。次章では、Chapter 5〜7 で作った FastAPI の OpenAPI ドキュメントから TypeScript の型を自動生成し、**バックエンドと型を共有した状態で fetch する** 仕組みを作ります。
