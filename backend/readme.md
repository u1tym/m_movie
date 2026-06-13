# 動画視聴アプリ — バックエンド

FastAPI で実装した動画管理・再生 API です。  
API 仕様の詳細はリポジトリルートの `API_MOVIE_SPEC.md` を参照してください。

## 概要

| 項目 | 内容 |
|------|------|
| フレームワーク | FastAPI |
| DB | PostgreSQL（`movie` スキーマ） |
| ベースパス | `/api/v1/movie` |
| 認証 | JWT Cookie（本番）／デバッグ時は固定ユーザ ID |

## 前提条件

- Python 3.11 以上推奨
- PostgreSQL が起動していること
- `public.accounts` テーブルが存在すること
- `movie` スキーマのテーブルが作成済みであること（`DB/1_db.sql`）

## セットアップ

### 1. 仮想環境の作成と依存パッケージのインストール

**必ず `backend` ディレクトリで** 以下を実行します。

```bash
cd backend
python -m venv env
env\Scripts\activate        # Windows
# source env/bin/activate   # Linux / macOS
pip install -r requirements.txt
```

### 2. 環境変数ファイルの作成

`backend/.env.example` をコピーして `backend/.env` を作成し、値を編集します。

```bash
copy .env.example .env      # Windows
# cp .env.example .env      # Linux / macOS
```

`.env` は **`backend` ディレクトリ（uvicorn 起動時のカレントディレクトリ）** から読み込まれます。

| 変数名 | 説明 | 例 |
|--------|------|-----|
| `DB_HOST` | DB ホスト | `localhost` |
| `DB_PORT` | DB ポート | `5432` |
| `DB_NAME` | データベース名 | `tamtdb` |
| `DB_USER` | DB ユーザー | `tamtuser` |
| `DB_PASSWORD` | DB パスワード | （任意） |
| `DEBUG` | デバッグモード | `true` / `false` |
| `DEBUG_AID` | デバッグ時に使用するアカウント ID | `1` |
| `SECRET_KEY` | JWT 署名鍵（本番必須） | 認証 API と同一の値 |
| `ALGORITHM` | JWT アルゴリズム | `HS256` |
| `COOKIE_NAME` | JWT Cookie 名 | `access_token` |
| `CORS_ORIGINS` | 許可オリジン（カンマ区切り） | `http://localhost:5173` |

### 3. データベースの準備

```bash
psql -U tamtuser -d tamtdb -f ../DB/1_db.sql
```

`DEBUG_AID` に指定した ID が `public.accounts` に存在する必要があります。

## 起動方法

**`backend` ディレクトリで** uvicorn を起動します。

```bash
cd backend
env\Scripts\activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

起動後の確認:

| URL | 説明 |
|-----|------|
| http://127.0.0.1:8000/health | 稼働確認（`debug` フラグも返却） |
| http://127.0.0.1:8000/docs | Swagger UI |

起動ログに次のような行が出れば `.env` の読み込みに成功しています。

```
Movie API started: DEBUG=True, DEBUG_AID=1, env_file=D:\...\backend\.env
```

## デバッグモード

`DEBUG=true` のとき:

- JWT 検証をスキップする
- すべてのリクエストを `DEBUG_AID` のユーザとして処理する
- フロントエンド開発時は、フロント側も `VITE_DEBUG=true` にするとセッション延長 API をスキップできる

`DEBUG=false`（本番）のとき:

- HttpOnly Cookie の JWT を検証する
- `SECRET_KEY`・`ALGORITHM`・`COOKIE_NAME` は認証 API と同一である必要がある
- JWT の `sub` クレームをアカウント ID として使用する

## 主なエンドポイント

ベースパス: `/api/v1/movie`

| メソッド | パス | 説明 |
|---------|------|------|
| GET | `/genres` | ジャンル一覧 |
| POST | `/genres` | ジャンル追加 |
| GET | `/series` | 作品一覧 |
| POST | `/series` | 作品登録 |
| GET | `/videos` | 動画一覧 |
| POST | `/videos` | 動画登録（メタデータ） |
| PUT | `/videos/{id}` | 動画編集 |
| DELETE | `/videos/{id}` | 動画削除 |
| POST | `/videos/{id}/chunks` | チャンクアップロード |
| POST | `/videos/{id}/complete` | アップロード完了 |
| GET | `/videos/{id}/chunks/{index}` | チャンク取得 |
| POST | `/videos/{id}/playback/start` | 再生開始 |
| PUT | `/videos/{id}/playback/state` | 再生位置保存 |

一覧は `API_MOVIE_SPEC.md` を参照してください。

## ディレクトリ構成

```
backend/
  app/
    main.py           # エントリポイント
    config.py         # 設定（.env 読み込み）
    database.py       # DB 接続
    dependencies.py   # 認証・エラーハンドラ
    models.py         # SQLAlchemy モデル
    routers/          # API ルート
    schemas/          # Pydantic スキーマ
    services/         # ビジネスロジック
    security/         # JWT 検証
  requirements.txt
  .env.example
  .env              # 各自作成（git 管理外）
```

## トラブルシューティング

### 「認証が必要です」と表示される

- `backend/.env` に `DEBUG=true` が設定されているか確認する
- **必ず `backend` ディレクトリから** uvicorn を起動する（`.env` はカレントディレクトリから読み込む）
- 起動後 `GET /health` で `"debug": true` になるか確認する
- `.env` 変更後は uvicorn を再起動する

### DB 接続エラー

- PostgreSQL が起動しているか確認する
- `DB_HOST` / `DB_PORT` / `DB_NAME` / `DB_USER` / `DB_PASSWORD` を確認する
- `DB/1_db.sql` が実行済みか確認する

## 関連ドキュメント

| ファイル | 内容 |
|----------|------|
| `API_MOVIE_SPEC.md` | API 仕様 |
| `DB_MOVIE_SPEC.md` | DB 設計 |
| `DB/1_db.sql` | テーブル作成 SQL |
| `API_LOGIN_SPEC.md` | 認証 API 仕様 |
