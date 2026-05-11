# Chapter 9: JS/TS おさらい (外部リンク集)

[← 目次に戻る](../README.md)

## この章について

Chapter 10 以降では **Next.js (TypeScript)** を使ってフロントエンドを実装していきます。

この章では、TypeScript / JavaScript に馴染みのない方が **最低限押さえておくべき概念** と **学習リソースへのリンク** をまとめています。

> **すでに TypeScript の経験がある方**  
> この章はスキップして [Chapter 10](../chapter10/README.md) に進んでください。

---

## 推奨する学習リソース

### TypeScript

| リソース | 内容 | 推奨度 |
|---|---|---|
| [サバイバル TypeScript](https://typescriptbook.jp/) | 日本語で最も網羅的な TypeScript 入門。実践的で読みやすい | ⭐⭐⭐ |
| [TypeScript 公式 Handbook](https://www.typescriptlang.org/docs/handbook/intro.html) | 公式のリファレンス。英語だが正確 | ⭐⭐ |
| [TypeScript Deep Dive (日本語)](https://typescript-jp.gitbook.io/deep-dive) | 詳細な解説。上級者向けだが「なぜそうなるか」が分かる | ⭐⭐ |

### JavaScript

| リソース | 内容 | 推奨度 |
|---|---|---|
| [JavaScript Primer](https://jsprimer.net/) | 日本語の JS 入門書。ゼロからしっかり学べる | ⭐⭐⭐ |
| [MDN Web Docs - JavaScript](https://developer.mozilla.org/ja/docs/Web/JavaScript) | Mozilla の公式リファレンス。関数ごとの詳細な解説 | ⭐⭐⭐ |
| [JavaScript.info](https://ja.javascript.info/) | モダン JS チュートリアル。日本語あり | ⭐⭐ |

### React

| リソース | 内容 | 推奨度 |
|---|---|---|
| [React 公式チュートリアル](https://ja.react.dev/learn) | 2023 年にリニューアルされた新しい公式ドキュメント。Hooks ベース | ⭐⭐⭐ |
| [React 公式 - Thinking in React](https://ja.react.dev/learn/thinking-in-react) | React の考え方を学ぶ最初の 1 ページ | ⭐⭐⭐ |
| [Next.js - React Foundations](https://nextjs.org/learn/react-foundations) | Next.js 公式が提供する React 基礎コース。React を Next.js の文脈で学べる | ⭐⭐⭐ |

### Next.js

| リソース | 内容 | 推奨度 |
|---|---|---|
| [Next.js - Learn (Dashboard App)](https://nextjs.org/learn/dashboard-app) | Next.js 公式のハンズオンチュートリアル。App Router でダッシュボードアプリを作りながら、ルーティング・データフェッチ・認証などを一通り体験できる | ⭐⭐⭐ |
| [Next.js 公式ドキュメント](https://nextjs.org/docs) | App Router、Server Components、API Routes など公式リファレンス | ⭐⭐ |

---

## Chapter 10 以降で必要になる最低限の知識

以下の概念は Chapter 10 以降で頻出します。「聞いたことはあるが自信がない」ものがあれば、上のリソースで事前に確認しておくことをおすすめします。

### JavaScript の基礎

| 概念 | 使う場面 |
|---|---|
| **変数宣言** (`const`, `let`) | あらゆる場所 |
| **アロー関数** (`() => { ... }`) | コンポーネント定義、コールバック |
| **テンプレートリテラル** (`` `Hello ${name}` ``) | 文字列組み立て |
| **分割代入** (`const { id, name } = user`) | props の受け取り、API レスポンスの展開 |
| **スプレッド構文** (`{ ...obj, key: value }`) | state の更新、オブジェクトのマージ |
| **配列メソッド** (`map`, `filter`, `find`) | リスト描画、データ加工 |
| **Promise / async / await** | API 呼び出し（fetch） |
| **モジュール** (`import` / `export`) | ファイル間のコード共有 |

### TypeScript の基礎

| 概念 | 使う場面 |
|---|---|
| **型注釈** (`name: string`, `age: number`) | 変数、関数引数、戻り値 |
| **インターフェース / 型エイリアス** (`interface User { ... }` / `type User = { ... }`) | API レスポンスの型定義、props の型定義 |
| **ジェネリクス** (`Array<T>`, `Promise<T>`) | 配列やライブラリの型引数 |
| **Union 型** (`string \| null`) | Optional な値の表現 |
| **型推論** | TypeScript が型を自動で推定してくれる仕組み |

### React の基礎

| 概念 | 使う場面 |
|---|---|
| **コンポーネント** (関数コンポーネント) | UI のパーツを作る |
| **JSX** | HTML に似た構文で UI を記述する |
| **props** | 親コンポーネントから子に値を渡す |
| **useState** | コンポーネント内の状態管理 |
| **useEffect** | 副作用（API 呼び出し、イベント登録） |
| **条件付きレンダリング** (`{isLoggedIn && <Component />}`) | 状態に応じた表示切り替え |
| **リストレンダリング** (`items.map(item => <Item key={item.id} />)`) | 配列からリストを描画 |

> **React を初めて触る方へ**  
> [React 公式チュートリアル](https://ja.react.dev/learn) を **Chapter 10 に入る前に最後までやる** ことを強く推奨します。30 分〜1 時間程度で完了する内容ですが、React の考え方（宣言的 UI、状態管理、コンポーネントの分割）を一通り体験できます。

---

## 次の章

[Chapter 10: Next.js 入門 + Tailwind CSS 基礎 →](../chapter10/README.md)
