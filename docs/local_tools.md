
# ■ DuckDB

- [DuckDB Docs | DuckDB](https://duckdb.org/docs/stable/)

## PostgreSQL との接続

- [PostgreSQL Extension | DuckDB](https://duckdb.org/docs/stable/core_extensions/postgres)


```bash
duckdb
```


```sql
-- postgres 拡張機能のインストールとロード
INSTALL postgres;
LOAD postgres;


-- PostgreSQL への接続情報をシークレットとして作成
CREATE SECRET (
    TYPE postgres,
    HOST 'web-tutorial-v2-sample-postgresql',
    PORT 5432,
    DATABASE sample,
    USER 'app',
    PASSWORD 'root1234'
);

-- シークレットを使って(一部設定を上書きして)PostgreSQL データベースを読み込み専用でアタッチ
ATTACH 'dbname= sample' AS postgres_db (TYPE postgres, READ_ONLY);


-- PostgreSQL データベース内のテーブル一覧を確認
SHOW ALL TABLES;
```


## Headless Chrome

```bash
# devcontainer上でheadlessモードでchromeを起動
# --no-sandbox: コンテナではnamespace, setuidなどが制限されているため、サンドボックス機能を無効化
# --disable-gpu: Dockerコンテナ内ではGPUが利用できない場合が多いため、GPUアクセラレーションを無効化
# --disable-dev-shm-usage: Docker の /dev/shm は デフォルトで 64MBであるため、共有メモリ(/dev/shm)の使用を無効化して、メモリ不足によるクラッシュを防止
google-chrome \
  --headless=new \
  --no-sandbox \
  --disable-gpu \
  --disable-dev-shm-usage


# devcontainer上でheadlessモードでchromeを起動してスクリーンショットを取得
google-chrome \
  --headless=new \
  --no-sandbox \
  --disable-gpu \
  --disable-dev-shm-usage \
  --screenshot=tmp/google.png \
  https://google.com
```