# Chapter 2: FastAPI 入門

[← 目次に戻る](../README.md)

## この章のゴール

- FastAPI で **パスパラメータ** と **クエリパラメータ** を扱える
- `Request` / `Response` を直接使った「**昔ながらの Web アプリ**」を実装し、Web の素朴な仕組みを体感する
- 「レガシーな Web アプリ」の問題点を整理し、なぜ **API + フロントエンド分離** がモダンな主流になったのかを理解する
- FastAPI 本来の書き方（**Pydantic + 型注釈 + `response_model`**）で同じ機能を再実装し、改善点を体感する

## スタート地点

```bash
git checkout chapter02-start
```

## 完成形

```bash
git checkout chapter02-end
```

---

## はじめに

Chapter 1 では FastAPI を Docker Compose で起動するところまで行きました。`/` にアクセスすると `{"message": "Hello World"}` が返ってくるだけのシンプルな状態です。

この章では、その `app/main.py` にエンドポイントを追加していきます。

この章は**Web 開発初心者の方向け**に、あえて遠回りをします。具体的には：

1. まず FastAPI の基本（パス・クエリパラメータ）を軽く触る
2. **わざと昔ながらの「HTML を直接返す Web アプリ」を実装してみる**
3. その問題点を整理する
4. **FastAPI 本来の書き方（API として JSON を返す）で再実装する**

この遠回りをすることで、「なぜ FastAPI のようなフレームワークがあるのか」「なぜ近年は API とフロントエンドを分離するのか」が体感できます。

> **すでに Web 開発経験がある方へ**
> 「レガシーな Web アプリの実装」のセクションは飛ばしても構いません。ただし「レガシーな Web アプリは何がダメなのか」のセクションは、後続の章にも繋がる考え方なので軽く目を通してください。

### 動作確認の進め方

Chapter 1 で `docker compose up` を起動済みの前提で進めます。Uvicorn の `--reload` フラグが効いているので、`backend/app/main.py` を編集して保存するたびにアプリが自動で再起動します。**コードを追記したら、すぐにブラウザや `curl` で動作確認** してください。

起動していない場合は以下で起動してください：

```bash
cd $PROJECT_DIR
docker compose up
```

---

## 1. 簡単な API を実装してみよう

まずは FastAPI の基本である **パスパラメータ** と **クエリパラメータ** を使った API を実装します。

`backend/app/main.py` を以下のように書き換えます（Chapter 1 で書いた `read_root` も残します）。

```python
# backend/app/main.py
from fastapi import FastAPI

app = FastAPI()


@app.get("/")
def read_root():
    return {"message": "Hello World"}


@app.get("/users/{user_id}")
def read_user(
    user_id: int,        # パスパラメータ (URL の {user_id} にマッチ)
    query: str = "",     # クエリパラメータ (?query=xxx)
):
    return {"user_id": user_id, "query": query}
```

### 解説

- **`@app.get("/users/{user_id}")`** … FastAPI のインスタンス `app` に「`GET /users/{user_id}` というルートを登録」する
- **`user_id: int`** … URL のプレースホルダ `{user_id}` を受け取る。型を `int` と書くだけで、FastAPI が文字列を整数に自動変換する
- **`query: str = ""`** … 引数にデフォルト値があるとクエリパラメータとして扱われる

### 動作確認

```bash
curl "http://web-tutorial-v2-backend-${HOST_USER}:8000/users/1?query=hello"
# {"user_id":1,"query":"hello"}
```

ブラウザから http://localhost:8000/users/1?query=hello でも同じ結果になります。

http://localhost:8000/docs を開いて、**Swagger UI** から API を実行することもできます。

> **型違反は何が起きる？**
> http://localhost:8000/users/abc にアクセスしてみてください。`abc` は整数ではないので、FastAPI が自動で `422 Unprocessable Entity` を返します。**型を書くだけでバリデーションが効く** のが FastAPI の特徴です。

---

## 2. レガシーな Web アプリの実装

### 2.1 Request と Response を確認する

FastAPI 本来の書き方では `Request` / `Response` を直接扱うことはほぼありませんが、**直接扱う書き方も可能** です。これを使って HTTP リクエスト/レスポンスの中身を覗いてみます。

- [Request](https://www.starlette.io/requests/) … HTTP リクエストを表すオブジェクト。URL、HTTP メソッド、ヘッダ、ボディなどを保持
- [Response](https://www.starlette.io/responses/) … HTTP レスポンスとなるオブジェクト。ボディ、ヘッダ、ステータスコードを指定

`backend/app/main.py` の末尾に以下を追加します：

```python
# backend/app/main.py
import json
from fastapi import FastAPI, Request, Response

# --- 既存のコード ---


@app.get("/info/{id}", tags=["Info"])
async def info_get(request: Request):
    body = {
        "url": str(request.url),
        "method": request.method,
        "headers": dict(request.headers),
        "query_params": dict(request.query_params),
        "path_params": dict(request.path_params),
        "client": str(request.client),
        "cookie": dict(request.cookies),
        "body": (await request.body()).decode("utf-8"),
    }
    return Response(
        content=json.dumps(body, ensure_ascii=False),
        status_code=200,
        headers={"Content-Type": "application/json"},
    )


@app.post("/info/{id}", tags=["Info"])
async def info_post(request: Request):
    body = {
        "url": str(request.url),
        "method": request.method,
        "headers": dict(request.headers),
        "query_params": dict(request.query_params),
        "path_params": dict(request.path_params),
        "client": str(request.client),
        "cookie": dict(request.cookies),
        "body": (await request.body()).decode("utf-8"),
    }
    return Response(
        content=json.dumps(body, ensure_ascii=False),
        status_code=200,
        headers={"Content-Type": "application/json"},
    )
```

> **`tags=["Info"]`** … Swagger UI でエンドポイントをグループ化するための指定。後で「Legacy」「Modern」のグループも作っていきます。

### 動作確認

GET リクエスト：

```bash
curl -s "http://web-tutorial-v2-backend-${HOST_USER}:8000/info/1?foo=bar" | jq .
# {
#   "url": "http://web-tutorial-v2-backend-ktamido:8000/info/1?foo=bar",
#   "method": "GET",
#   "headers": {
#     "host": "web-tutorial-v2-backend-ktamido:8000",
#     "user-agent": "curl/8.5.0",
#     "accept": "*/*"
#   },
#   "query_params": {
#     "foo": "bar"
#   },
#   "path_params": {
#     "id": "1"
#   },
#   "client": "Address(host='172.21.0.2', port=58022)",
#   "cookie": {},
#   "body": ""
# }
```

レスポンスに `query_params` として `{"foo": "bar"}` が含まれているはずです。

POST リクエスト：

```bash
curl -s -X POST \
    "http://web-tutorial-v2-backend-${HOST_USER}:8000/info/100" \
    -H 'Content-Type: application/json' \
    -d '{"foo": "bar", "hoge": "fuga"}' | jq .

# {
#   "url": "http://web-tutorial-v2-backend-ktamido:8000/info/100",
#   "method": "POST",
#   "headers": {
#     "host": "web-tutorial-v2-backend-ktamido:8000",
#     "user-agent": "curl/8.5.0",
#     "accept": "*/*",
#     "content-type": "application/json",
#     "content-length": "30"
#   },
#   "query_params": {},
#   "path_params": {
#     "id": "100"
#   },
#   "client": "Address(host='172.21.0.2', port=57210)",
#   "cookie": {},
#   "body": "{\"foo\": \"bar\", \"hoge\": \"fuga\"}"
# }
```

レスポンスの `body` に送信した JSON 文字列が含まれます。

> **HTTP リクエスト・レスポンスとは何か**
> ブラウザや `curl` がサーバーに送るのが **リクエスト**（URL・メソッド・ヘッダ・ボディなど）、サーバーが返すのが **レスポンス**（ステータスコード・ヘッダ・ボディなど）です。普段ブラウザで Web ページを見るときも、裏でこの一往復が起きています。

### 2.2 アイテム一覧（HTML を返す）

ここからは「**HTML を直接返すレガシーな Web アプリ**」を作っていきます。

サーバーが返すのが `application/json` だと API、`text/html` だとブラウザはレンダリングして画面として表示します。**Web の本質はサーバーが文字列を返してブラウザが解釈すること**であることを体感しましょう。

スタイリングは [Bootstrap](https://getbootstrap.com/) の CDN を読み込んで簡単に済ませます。

`backend/app/main.py` の末尾に以下を追加します：

```python
# backend/app/main.py

# --- 既存のコード ---


ITEMS = {
    1: {"id": 1, "name": "Apple", "price": 100},
    2: {"id": 2, "name": "Banana", "price": 200},
    3: {"id": 3, "name": "Orange", "price": 150},
}


@app.get("/items/", tags=["Legacy"])
async def read_items_get(request: Request):
    search = request.query_params.get("search", None)
    rows = []
    for id, e in ITEMS.items():
        if search and (search.lower() not in e["name"].lower()):
            continue
        row = f"""
            <tr>
              <th scope="row"><a href="/items/{id}">{id}</a></th>
              <td>{e["name"]}</td>
              <td>{e["price"]}</td>
            </tr>
        """
        rows.append(row)
    html = f"""
    <!DOCTYPE html>
    <html>
      <head>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
      </head>
      <body class="container">
        <p class="fs-1"><a href="/items/">App</a></p>
        <a class="btn btn-primary" href="/items/create/" role="button">Create</a>
        <table class="table table-striped">
          <thead>
            <tr>
              <th scope="col">ID</th>
              <th scope="col">Name</th>
              <th scope="col">Price</th>
            </tr>
          </thead>
          <tbody>
            {''.join(rows)}
          </tbody>
        </table>
      </body>
    </html>
    """
    return Response(
        content=html,
        status_code=200,
        headers={"Content-Type": "text/html; charset=UTF-8"},
    )
```

`ITEMS` はモジュールレベルの辞書として定義しています。本来ならデータベースに保存しますが、Chapter 3 で PostgreSQL に置き換えるまでの **暫定的なインメモリストレージ** です。変更はアプリを再起動すると揮発します。

### 動作確認

ブラウザで http://localhost:8000/items/ を開くと、Bootstrap でスタイリングされたアイテム一覧の表が表示されます。

http://localhost:8000/items/?search=app と検索クエリを付けると Apple のみが表示されます。

> **HTML を返しているだけ**
> ブラウザの DevTools (F12) を開いて Network タブを見てみると、`http://localhost:8000/items/` に対するレスポンスが `text/html` で、サーバーは HTML 文字列を返しているだけです。それをブラウザが解釈して画面を組み立てているのが Web の素朴な仕組みです。

### 2.3 アイテム詳細

パスパラメータで指定された `item_id` のアイテムを HTML で表示します。存在しない ID の場合は `404 Not Found` を返します。

```python
# backend/app/main.py の末尾に追加

@app.get("/items/{item_id}", tags=["Legacy"])
async def read_item_get(request: Request):
    item_id = int(str(request.path_params.get("item_id")))
    if item_id not in ITEMS:
        return Response(
            content=f"<h1>ID={item_id} Not Found</h1>",
            status_code=404,
            headers={"Content-Type": "text/html; charset=UTF-8"},
        )
    item = ITEMS[item_id]
    html = f"""
    <!DOCTYPE html>
    <html>
      <head>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
      </head>
      <body class="container">
        <p class="fs-1"><a href="/items/">App</a></p>
        <form action="/items/{item_id}/delete/" method="post">
          <button type="submit" class="btn btn-danger">Delete</button>
        </form>
        <ul class="list-group">
          <li class="list-group-item">ID: {item_id}</li>
          <li class="list-group-item">Name: {item["name"]}</li>
          <li class="list-group-item">Price: {item["price"]}</li>
        </ul>
      </body>
    </html>
    """
    return Response(
        content=html,
        status_code=200,
        headers={"Content-Type": "text/html; charset=UTF-8"},
    )
```

### 動作確認

- http://localhost:8000/items/1 … `id=1` のアイテム詳細
- http://localhost:8000/items/100 … 存在しないので 404

### 2.4 アイテム新規作成

新規作成は **2 つの API** が必要です。

| メソッド | パス | 役割 |
|---|---|---|
| GET | `/items/create/` | 登録フォームの HTML を返す |
| POST | `/items/create/` | フォームから送信された値を受け取って保存 |

```python
# backend/app/main.py の末尾に追加

@app.get("/items/create/", tags=["Legacy"])
async def create_item_get(request: Request):
    html = """
    <!DOCTYPE html>
    <html>
      <head>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
      </head>
      <body class="container">
        <p class="fs-1"><a href="/items/">App</a></p>
        <form action="/items/create/" method="post">
          <div class="mb-3">
            <label for="id" class="form-label">ID</label>
            <input type="number" name="id" class="form-control" id="id" required>
          </div>
          <div class="mb-3">
            <label for="name" class="form-label">Name</label>
            <input type="text" name="name" class="form-control" id="name" required>
          </div>
          <div class="mb-3">
            <label for="price" class="form-label">Price</label>
            <input type="number" name="price" class="form-control" id="price" required>
          </div>
          <button type="submit" class="btn btn-primary">Submit</button>
        </form>
      </body>
    </html>
    """
    return Response(
        content=html,
        status_code=200,
        headers={"Content-Type": "text/html; charset=UTF-8"},
    )


@app.post("/items/create/", tags=["Legacy"])
async def create_item_post(request: Request):
    form = await request.form()
    id = int(str(form["id"]))
    name = str(form["name"])
    price = int(str(form["price"]))
    if id in ITEMS:
        return Response(
            content=f"<h1>ID={id} Already Exists</h1>",
            status_code=400,
            headers={"Content-Type": "text/html; charset=UTF-8"},
        )
    ITEMS[id] = {"id": id, "name": name, "price": price}
    return Response(
        status_code=302,
        headers={"Location": f"/items/{id}"},
    )
```

### 動作確認

http://localhost:8000/items/create/ を開いてフォームに値を入力 → Submit をクリック。登録が成功するとアイテム詳細ページにリダイレクトされます。

> **`status_code=302`** とは
> リダイレクトを表す HTTP ステータスコードです。レスポンスの `Location` ヘッダで指定された URL にブラウザが自動で再アクセスします。
> POST してそのまま POST のレスポンスを画面に表示するのではなく、別のURLにGETでリダイレクトする手法は **Post-Redirect-Get (PRG) パターン** と呼ばれ、結果画面の再読み込みでフォームが二重送信されるのを防ぐ目的で利用されます。

### 2.5 アイテム削除

アイテム詳細ページの **Delete** ボタンが押されたときに POST されます。

```python
# backend/app/main.py の末尾に追加

@app.post("/items/{item_id}/delete/", tags=["Legacy"])
async def delete_item_post(request: Request):
    item_id = int(str(request.path_params.get("item_id")))
    if item_id not in ITEMS:
        return Response(
            content=f"<h1>ID={item_id} Not Found</h1>",
            status_code=404,
            headers={"Content-Type": "text/html; charset=UTF-8"},
        )
    del ITEMS[item_id]
    return Response(
        status_code=302,
        headers={"Location": "/items/"},
    )
```

### 動作確認

http://localhost:8000/items/1 を開いて Delete ボタンをクリック → 一覧にリダイレクトされ、`id=1` のアイテムが消えています。

---

## 3. レガシーな Web アプリは何がダメなのか

ここまで「HTML を直接返すレガシーな Web アプリ」を実装してきました。隠蔽されている部分が少ないので分かりやすかった反面、コードが冗長で大変だったかと思います。

ではこのスタイルの問題点を整理します。

### 3.1 リクエストで受け取るパラメータとその型が明確ではない

アイテム新規作成 API (POST) を見てみましょう。

```python
@app.post("/items/create/", tags=["Legacy"])
async def create_item_post(request: Request):
    form = await request.form()
    id = int(str(form["id"]))
    name = str(form["name"])
    price = int(str(form["price"]))
    # ...
```

**この関数が何を受け取るのか、関数のシグネチャからは全く分かりません**。`request: Request` としか書いておらず、必要なパラメータが `Request` オブジェクトに隠蔽されています。

これは以下の問題を生みます：

- コードを読まないと API の使い方が分からない（**ドキュメント化が困難**）
- リファクタリングや変更が難しい（**型チェックが効かない**）
- テストで考慮すべきパターンが膨大になる

### 3.2 レスポンスで返す値とその型が明確ではない

アイテム一覧 API を見てみましょう。HTML 文字列を返すコードからは、**どんなデータをどんな構造で返しているか** がパッと見では分かりません。

```python
@app.get("/items/", tags=["Legacy"])
async def read_items_get(request: Request):
    # ... HTML 文字列を組み立てて返す ...
```

これはテストの書きにくさに直結します。HTML をパースして「`<td>` の中身が期待通りか」を検証することはできますが、HTML 文字列になった時点で **型情報が失われている** ので厳密なチェックは困難です。

### 3.3 処理とデザインが密結合している

HTML を返す API は、必ず処理（データの取得・加工）とデザイン（HTML 構造・スタイル）が同じ関数の中に書かれます。

これにより以下の問題が起きます：

- **API の再利用ができない**: 似た処理を別画面でも使いたいとき、HTML がくっついていると再利用できない
- **変更時の考慮事項が増える**: 「処理だけ変えたい」のにデザインも考慮しないといけない（逆も同じ）
- **役割分担しにくい**: バックエンドエンジニアとフロントエンドエンジニアが同じファイルを編集することになる

特に、近年は **同じ API を Web ブラウザ・スマホアプリ・別のサーバーから呼ぶ** ことが当たり前になりました。HTML を返す API はブラウザからしか使えないので、この多様な利用形態に対応できません。

---

## 4. モダンな API へ

これらの問題を FastAPI 本来の書き方で解決していきます。

| 問題 | 解決法 |
|---|---|
| パラメータと型が不明 | パスパラメータ・クエリパラメータ・リクエストボディを **関数の引数として型付きで定義** |
| レスポンスの型が不明 | デコレータの **`response_model`** で返却する型を明示 |
| 処理とデザインの密結合 | API は **JSON だけを返す**。デザインはフロントエンド側のフレームワーク（Next.js など）に任せる |

### 4.1 アイテム一覧

`backend/app/main.py` の末尾に以下を追加します：

```python
# backend/app/main.py
from fastapi import HTTPException
from pydantic import BaseModel

# --- 既存のコード ---


class ItemSchema(BaseModel):
    id: int
    name: str
    price: int


class ItemsSchema(BaseModel):
    items: list[ItemSchema]


@app.get("/api/items/", response_model=ItemsSchema, tags=["Modern"])
async def read_items_api(
    search: str | None = None,
):
    items = []
    for _, e in ITEMS.items():
        if search and (search.lower() not in e["name"].lower()):
            continue
        items.append(e)
    return {"items": items}
```

### 解説

- **`class ItemSchema(BaseModel)`** … Pydantic の `BaseModel` を継承したクラス。フィールドの型を宣言するだけで、バリデーションと JSON シリアライズが自動で行われます
- **`search: str | None = None`** … クエリパラメータを **関数の引数として型付きで宣言**。Python 3.10 以降は `Optional[str]` の代わりに `str | None` と書けます
- **`response_model=ItemsSchema`** … この API が返す型を宣言。指定された型と異なる値を返すと `500 Internal Server Error` になります

### 動作確認

```bash
curl -s "http://web-tutorial-v2-backend-${HOST_USER}:8000/api/items/" | jq .
# {
#   "items": [
#     {"id": 1, "name": "Apple", "price": 100},
#     ...
#   ]
# }
```

http://localhost:8000/docs を開くと、`Modern` グループに `GET /api/items/` が登録され、**`search` クエリパラメータの存在と型** がドキュメントとして自動表示されます。`Responses` セクションの `Schema` にはレスポンスとして返却されるデータの構造も載っています。これが「型が明確であるとは何か」の体感です。

### 4.2 アイテム詳細

```python
# backend/app/main.py の末尾に追加

@app.get("/api/items/{item_id}", response_model=ItemSchema, tags=["Modern"])
async def read_item_api(item_id: int):
    if item_id not in ITEMS:
        raise HTTPException(status_code=404, detail=f"ID={item_id} not found")
    return ITEMS[item_id]
```

### 解説

- **`HTTPException`** … FastAPI が用意しているエラー応答用の例外。`raise` するだけで `status_code` と `detail` を含む JSON エラーレスポンスが返ります
- **`item_id: int`** … パスパラメータも型付きで宣言。`/api/items/abc` のような不正な値は FastAPI が自動で `422` で弾きます

### 動作確認

```bash
curl -s "http://web-tutorial-v2-backend-${HOST_USER}:8000/api/items/1" | jq .
# {"id": 1, "name": "Apple", "price": 100}

curl -s "http://web-tutorial-v2-backend-${HOST_USER}:8000/api/items/100" | jq .
# {"detail": "ID=100 not found"}

curl -s "http://web-tutorial-v2-backend-${HOST_USER}:8000/api/items/abc" | jq .
# {
#   "detail": [
#     {
#       "type": "int_parsing",
#       "loc": ["path", "item_id"],
#       "msg": "Input should be a valid integer, unable to parse string as an integer",
#       "input": "abc"
#     }
#   ]
# }
```

### 4.3 アイテム新規作成

```python
# backend/app/main.py の末尾に追加

@app.post("/api/items/create/", response_model=ItemSchema, tags=["Modern"])
async def create_item_api(body: ItemSchema):
    if body.id in ITEMS:
        raise HTTPException(status_code=400, detail=f"ID={body.id} already exists")
    item = {"id": body.id, "name": body.name, "price": body.price}
    ITEMS[body.id] = item
    return item
```

### 解説

- **`body: ItemSchema`** … リクエストボディを **Pydantic モデルの型で受け取る**。型が違うフィールドや欠損があると `422` で自動的に弾かれます

### 動作確認

```bash
curl -s -X POST "http://web-tutorial-v2-backend-${HOST_USER}:8000/api/items/create/" \
  -H 'Content-Type: application/json' \
  -d '{"id": 4, "name": "Grape", "price": 300}' | jq .
# {"id": 4, "name": "Grape", "price": 300}
```

不正なリクエストの例：

```bash
curl -s -X POST "http://web-tutorial-v2-backend-${HOST_USER}:8000/api/items/create/" \
  -H 'Content-Type: application/json' \
  -d '{"id": "not_an_int", "name": "Grape"}' | jq .
# 422 Unprocessable Entity が返り、どのフィールドが何の理由で不正かが詳細に説明される

# {
#   "detail": [
#     {
#       "type": "int_parsing",
#       "loc": [ "body", "id" ],
#       "msg": "Input should be a valid integer, unable to parse string as an integer",
#       "input": "not_an_int"
#     },
#     {
#       "type": "missing",
#       "loc": [ "body", "price" ],
#       "msg": "Field required",
#       "input": { "id": "not_an_int", "name": "Grape" }
#     }
#   ]
# }
```

### 4.4 アイテム削除

```python
# backend/app/main.py の末尾に追加

@app.delete("/api/items/{item_id}/", tags=["Modern"])
async def delete_item_api(item_id: int):
    if item_id not in ITEMS:
        raise HTTPException(status_code=404, detail=f"ID={item_id} not found")
    del ITEMS[item_id]
    return {"id": item_id}
```

### 動作確認

```bash
curl -s -X DELETE "http://web-tutorial-v2-backend-${HOST_USER}:8000/api/items/1/" | jq .
# {"id": 1}
```

---

## 5. 比較してみよう

http://localhost:8000/docs を開くと、3 つのグループが並んでいるはずです：

- **Info** … `Request` / `Response` の中身を覗く
- **Legacy** … HTML を直接返すレガシースタイル
- **Modern** … FastAPI 本来の API スタイル

同じ「アイテム CRUD」の機能が **Legacy** と **Modern** の両方で実装されています。Swagger UI を見比べてみましょう。

| 観点 | Legacy | Modern |
|---|---|---|
| パラメータの説明 | なし（`Request` の中身は分からない） | あり（型・必須・サンプル値が自動表示） |
| レスポンスの構造 | なし（HTML が返ることだけ） | あり（`Schemas` に `ItemSchema` が定義） |
| Try it out で実行 | できるが何を入れればいいか分からない | フォームが自動生成され、すぐ実行できる |
| エラーハンドリング | 自前で書く | 型違反は FastAPI が自動で `422` |

---

## 次の章

[Chapter 3: PostgreSQL + SQLAlchemy →](../chapter03/README.md)

ここまで `ITEMS` というモジュールレベルの辞書をストレージに使ってきました。アプリを再起動するとデータが消えてしまうので、次章では **PostgreSQL + SQLAlchemy** で永続化する方法を学びます。
