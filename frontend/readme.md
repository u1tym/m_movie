# 動画視聴アプリ — フロントエンド

Vue 3 + TypeScript + Vite で実装した動画視聴 Web アプリです。  
スマートフォン画面を主に想定し、PC からも利用できます。

## 概要

| 項目 | 内容 |
|------|------|
| フレームワーク | Vue 3 |
| 言語 | TypeScript |
| ビルドツール | Vite |
| ルーティング | Vue Router（Hash モード） |
| ベースパス | `/mobile/movie/` |

## 機能

| 画面 | 機能 |
|------|------|
| 動画一覧 | 一覧表示、ジャンル絞り込み、タイトル検索、ページング |
| 動画登録 | MP4 アップロード、サムネイル、作品・話数、ジャンル設定 |
| 動画編集 | タイトル・ジャンル等のメタデータ編集、削除 |
| 動画再生 | 再生／一時停止、シーク、次の動画、再生位置の保存 |
| プレイリスト | 一覧・作成・編集・順次再生 |
| 続きから視聴 | 単体動画 / プレイリストそれぞれの最終位置 |

## 前提条件

- Node.js 18 以上推奨
- 動画 API（`backend`）が起動していること
- 開発時: バックエンド `DEBUG=true`、フロント `VITE_DEBUG=true` を推奨

## セットアップ

```bash
cd frontend
npm install
```

### 環境変数

開発用は `frontend/.env.development` が自動的に読み込まれます。

```bash
# frontend/.env.development
VITE_DEBUG=true
```

本番ビルド用のテンプレートは `.env.example` を参照してください。

| 変数名 | 説明 | 開発時 | 本番時 |
|--------|------|--------|--------|
| `VITE_DEBUG` | `true` でセッション延長（`POST /refresh`）をスキップ | `true` 推奨 | `false` |
| `VITE_MOVIE_ORIGIN` | 動画 API の基点（末尾スラッシュなし） | プロキシ利用のため不要 | 例: `https://example.com/api/v1/movie` |
| `VITE_LOGIN_ORIGIN` | 認証 API の基点 | プロキシ利用のため不要 | 例: `https://example.com/api/auth` |
| `VITE_MOVIE_PROXY_TARGET` | 開発時プロキシ先（動画 API） | 省略時 `http://127.0.0.1:8000` | — |
| `VITE_LOGIN_PROXY_TARGET` | 開発時プロキシ先（認証 API） | 省略時 `http://127.0.0.1:8000` | — |

認証 API が別ポートで動いている場合は、例えば次のように設定します。

```
VITE_LOGIN_PROXY_TARGET=http://127.0.0.1:8001
```

## 開発サーバーの起動

### 1. バックエンドを起動

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. フロントエンドを起動

```bash
cd frontend
npm run dev
```

ブラウザで次の URL を開きます。

```
http://localhost:5173/mobile/movie/
```

### 開発時の API 接続（プロキシ）

開発時（`npm run dev`）は Vite のプロキシで CORS を回避します。

| フロントのパス | 転送先 |
|---------------|--------|
| `/api/movie/*` | `http://127.0.0.1:8000/api/v1/movie/*` |
| `/api/auth/*` | `http://127.0.0.1:8000/*`（認証 API） |

動画 API の実体は `http://127.0.0.1:8000` を基点とします。

## 認証の動作

### デバッグ時（推奨）

| 側 | 設定 | 動作 |
|----|------|------|
| バックエンド | `DEBUG=true` | JWT なしで `DEBUG_AID` を使用 |
| フロント | `VITE_DEBUG=true` | `POST /refresh` を呼ばない |

### 本番時

| 側 | 設定 | 動作 |
|----|------|------|
| バックエンド | `DEBUG=false` | JWT Cookie を検証 |
| フロント | `VITE_DEBUG=false` | 動画 API 呼び出し前に `POST /refresh` でセッション延長 |

本番では `withCredentials`（`fetch` の `credentials: 'include'`）により Cookie が送信されます。  
認証 API の仕様は `API_LOGIN_SPEC.md` を参照してください。

## ビルドとプレビュー

```bash
cd frontend
npm run build
npm run preview
```

本番ビルド前に、環境変数 `VITE_MOVIE_ORIGIN` と `VITE_LOGIN_ORIGIN` を正しく設定してください。

## ディレクトリ構成

```
frontend/
  src/
    api/              # API クライアント
    assets/           # スタイル
    components/       # 共通コンポーネント
    composables/      # 再生ロジック等
    router/           # ルーティング
    types/            # 型定義
    views/            # 画面
    config.ts         # API 基点の設定
    auth.ts           # セッション延長
  vite.config.ts      # プロキシ設定
  .env.development    # 開発用環境変数
  .env.example        # 本番用テンプレート
```

## 画面とルート

| パス | 画面 |
|------|------|
| `/#/` | 動画一覧 |
| `/#/register` | 動画登録 |
| `/#/videos/:id` | 動画再生 |
| `/#/videos/:id/edit` | 動画編集 |
| `/#/playlists` | プレイリスト一覧 |
| `/#/playlists/:id/edit` | プレイリスト編集 |
| `/#/playlists/:id/play` | プレイリスト再生 |

## 動画登録の流れ

1. タイトル・ジャンル等のメタデータを入力
2. MP4 ファイルを選択（長さはブラウザで自動取得）
3. `POST /videos` でメタデータ登録
4. ファイルを約 4MB ごとに分割して `POST /chunks` でアップロード
5. `POST /complete` で登録完了
6. 任意でサムネイル画像をアップロード

## 動画再生の流れ

1. `POST /playback/start` で再生情報を取得
2. チャンクを順に取得して結合し Blob URL を生成
3. HTML5 Video で再生（一時停止・シークはブラウザ標準機能 + カスタムシークバー）
4. 停止時および 10 秒ごとに `PUT /playback/state` で再生位置を保存

## トラブルシューティング

### 「認証が必要です」と表示される

- バックエンド `backend/.env` に `DEBUG=true` があるか確認する
- フロント `frontend/.env.development` に `VITE_DEBUG=true` があるか確認する
- バックエンドを `backend` ディレクトリから起動しているか確認する
- http://127.0.0.1:8000/health で `"debug": true` を確認する

### API に接続できない

- バックエンドが port 8000 で起動しているか確認する
- プロキシ先を変える場合は `VITE_MOVIE_PROXY_TARGET` を設定する
- ブラウザの開発者ツールで `/api/movie/` へのリクエスト URL を確認する

### 動画が再生できない

- 動画の `status` が `ready` であること（登録直後は `uploading`）
- MP4 形式のファイルであること
- チャンクのアップロードと `complete` が完了していること

## 関連ドキュメント

| ファイル | 内容 |
|----------|------|
| `API_MOVIE_SPEC.md` | 動画 API 仕様 |
| `API_LOGIN_SPEC.md` | 認証 API 仕様 |
| `backend/readme.md` | バックエンドの使用方法 |
