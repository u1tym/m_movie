# API 仕様書 — 動画視聴アプリ

## 1. 概要

ブラウザ上で動画を視聴・管理する Web アプリ向けの REST API 仕様。
DB 設計は `DB_MOVIE_SPEC.md`、テーブル定義は `DB/1_db.sql` を参照する。

| 項目 | 内容 |
|------|------|
| API バージョン | v1 |
| ベースパス | `/api/v1/movie` |
| データ形式 | JSON（バイナリ配信を除く） |
| 文字コード | UTF-8 |

### 1.1 認証とアカウント ID

- すべての API は認証済みリクエストを前提とする。
- **アカウント ID（`aid`）は API のリクエスト／レスポンスに含めない。** バックエンドがセッション・JWT 等から `aid` を取得し、DB アクセス時に付与する。
- 他ユーザーのリソースへのアクセスは `403 Forbidden` を返す。

### 1.2 機能一覧

| カテゴリ | 機能 |
|---------|------|
| ジャンル | 一覧取得、追加 |
| 作品 | 一覧取得、登録、詳細取得 |
| 動画 | 登録（チャンクアップロード）、削除、編集（メタデータのみ）、一覧取得、詳細取得 |
| サムネイル | 取得、登録（動画登録時または別途） |
| 再生 | 再生開始、チャンク取得、シーク、一時停止、再生位置保存、次の動画取得、視聴履歴 |

### 1.3 編集の制約

動画の編集 API では **メタデータ（タイトル、説明、ジャンル、作品・話数情報等）のみ変更可能** とする。
**動画ファイル（チャンク）の入れ替え・再アップロードは不可。** ファイルを変更する場合は削除後に新規登録とする。

---

## 2. 共通仕様

### 2.1 HTTP ステータスコード

| コード | 意味 | 使用例 |
|--------|------|--------|
| 200 | 成功 | GET、PUT の正常終了 |
| 201 | 作成成功 | POST によるリソース作成 |
| 204 | 成功（ボディなし） | DELETE |
| 400 | リクエスト不正 | バリデーションエラー |
| 401 | 未認証 | ログインなし・トークン無効 |
| 403 | 権限なし | 他ユーザーのリソース操作 |
| 404 | 未存在 | 指定 ID のリソースなし |
| 409 | 競合 | 話数重複、ジャンル名重複 |
| 422 | 処理不可 | アップロード未完了の動画への再生要求等 |
| 500 | サーバーエラー | 内部エラー |

### 2.2 エラーレスポンス形式

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "タイトルは必須です",
    "details": [
      { "field": "title", "message": "必須項目です" }
    ]
  }
}
```

### 2.3 ページネーション

一覧 API はクエリパラメータでページングする。

| パラメータ | 型 | デフォルト | 説明 |
|-----------|-----|-----------|------|
| `page` | int | `1` | ページ番号（1 始まり） |
| `per_page` | int | `20` | 1 ページあたり件数（最大 100） |

レスポンスに以下を含める。

```json
{
  "items": [],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total_count": 150,
    "total_pages": 8
  }
}
```

### 2.4 日時形式

ISO 8601（`2026-06-13T12:34:56+09:00`）を使用する。

---

## 3. データ型（共通オブジェクト）

### 3.1 Genre（ジャンル）

```json
{
  "genre_id": 1,
  "name": "洋画",
  "sort_order": 1,
  "is_system": true
}
```

| フィールド | 型 | 説明 |
|-----------|-----|------|
| `genre_id` | int | ジャンル ID |
| `name` | string | ジャンル名 |
| `sort_order` | int | 表示順 |
| `is_system` | boolean | システム共通ジャンルか（DB 上 `aid IS NULL`） |

### 3.2 Series（作品）

```json
{
  "series_id": 10,
  "title": "サンプル作品",
  "description": "作品の説明",
  "created_at": "2026-06-13T10:00:00+09:00",
  "updated_at": "2026-06-13T10:00:00+09:00"
}
```

### 3.3 VideoSummary（動画一覧用）

```json
{
  "video_id": 100,
  "title": "第1話 はじまり",
  "description": "動画の説明",
  "series_id": 10,
  "series_title": "サンプル作品",
  "episode_number": 1,
  "episode_title": "はじまり",
  "sort_order": 1,
  "duration_ms": 3600000,
  "mime_type": "video/mp4",
  "file_size_bytes": 524288000,
  "status": "ready",
  "genres": [
    { "genre_id": 1, "name": "アニメ" }
  ],
  "has_thumbnail": true,
  "position_ms": 120000,
  "completed": false,
  "created_at": "2026-06-13T10:00:00+09:00",
  "updated_at": "2026-06-13T10:00:00+09:00"
}
```

| フィールド | 型 | 説明 |
|-----------|-----|------|
| `position_ms` | int \| null | 最後の再生位置。未視聴は `null` |
| `completed` | boolean | 視聴完了済みか |
| `status` | string | `uploading` / `ready` / `error` / `deleted` |

### 3.4 VideoDetail（動画詳細）

`VideoSummary` に加え、以下を含む。

```json
{
  "chunk_count": 720,
  "last_played_at": "2026-06-13T15:30:00+09:00",
  "play_count": 3
}
```

### 3.5 PlaybackInfo（再生情報）

```json
{
  "video_id": 100,
  "title": "第1話 はじまり",
  "duration_ms": 3600000,
  "mime_type": "video/mp4",
  "chunk_count": 720,
  "position_ms": 120000,
  "completed": false,
  "status": "ready"
}
```

### 3.6 ChunkMeta（チャンクメタデータ）

```json
{
  "chunk_index": 12,
  "start_time_ms": 60000,
  "end_time_ms": 65000,
  "byte_length": 524288
}
```

---

## 4. ジャンル API

### 4.1 ジャンル一覧取得

システム共通ジャンルと、ログインユーザーが追加したジャンルを返す。

```
GET /api/v1/movie/genres
```

**レスポンス 200**

```json
{
  "items": [
    { "genre_id": 1, "name": "洋画", "sort_order": 1, "is_system": true },
    { "genre_id": 8, "name": "邦画名作", "sort_order": 10, "is_system": false }
  ]
}
```

---

### 4.2 ジャンル追加

ユーザー独自ジャンルを追加する。システムジャンルは追加不可。

```
POST /api/v1/movie/genres
```

**リクエストボディ**

```json
{
  "name": "邦画名作",
  "sort_order": 10
}
```

| フィールド | 型 | 必須 | 制約 |
|-----------|-----|------|------|
| `name` | string | ○ | 1〜100 文字。同一ユーザー内で重複不可 |
| `sort_order` | int | - | 0 以上。省略時 `0` |

**レスポンス 201** — `Genre` オブジェクト

**エラー**

| コード | 条件 |
|--------|------|
| 409 | 同名ジャンルが既に存在 |

---

## 5. 作品 API

### 5.1 作品一覧取得

```
GET /api/v1/movie/series
```

**クエリパラメータ**

| パラメータ | 型 | 説明 |
|-----------|-----|------|
| `page` | int | ページ番号 |
| `per_page` | int | 件数 |
| `q` | string | タイトル部分一致検索 |

**レスポンス 200** — `Series` のページネーション付き一覧

---

### 5.2 作品登録

```
POST /api/v1/movie/series
```

**リクエストボディ**

```json
{
  "title": "サンプル作品",
  "description": "作品の説明"
}
```

| フィールド | 型 | 必須 | 制約 |
|-----------|-----|------|------|
| `title` | string | ○ | 1〜500 文字 |
| `description` | string | - | 任意 |

**レスポンス 201** — `Series` オブジェクト

---

### 5.3 作品詳細取得

```
GET /api/v1/movie/series/{series_id}
```

**レスポンス 200** — `Series` に加え、紐づく動画の簡易リスト

```json
{
  "series_id": 10,
  "title": "サンプル作品",
  "description": "作品の説明",
  "videos": [
    {
      "video_id": 100,
      "episode_number": 1,
      "episode_title": "はじまり",
      "sort_order": 1,
      "duration_ms": 3600000,
      "status": "ready"
    }
  ],
  "created_at": "2026-06-13T10:00:00+09:00",
  "updated_at": "2026-06-13T10:00:00+09:00"
}
```

---

## 6. 動画 API

### 6.1 動画一覧取得

```
GET /api/v1/movie/videos
```

**クエリパラメータ**

| パラメータ | 型 | 説明 |
|-----------|-----|------|
| `page` | int | ページ番号 |
| `per_page` | int | 件数 |
| `genre_id` | int | ジャンル ID でフィルタ |
| `series_id` | int | 作品 ID でフィルタ |
| `status` | string | 状態フィルタ（省略時 `ready` のみ。`all` で全状態） |
| `q` | string | タイトル・話タイトル部分一致検索 |
| `sort` | string | ソートキー（`created_at` / `title` / `last_played_at`） |
| `order` | string | `asc` / `desc`（デフォルト `desc`） |

**レスポンス 200** — `VideoSummary` のページネーション付き一覧

**備考**

- `genre_id` 指定時は `video_genre` 経由で絞り込む。
- `sort=last_played_at` 時は `playback_state` を LEFT JOIN する。

---

### 6.2 動画詳細取得

```
GET /api/v1/movie/videos/{video_id}
```

**レスポンス 200** — `VideoDetail` オブジェクト

**エラー**

| コード | 条件 |
|--------|------|
| 404 | 動画が存在しない、または論理削除済み |

---

### 6.3 動画登録（メタデータ作成）

動画ファイル本体はチャンク API で別途アップロードする。本 API はメタデータの作成と `video_id` の払い出しを行う。

```
POST /api/v1/movie/videos
```

**リクエストボディ**

```json
{
  "title": "第1話 はじまり",
  "description": "動画の説明",
  "series_id": 10,
  "episode_number": 1,
  "episode_title": "はじまり",
  "sort_order": 1,
  "duration_ms": 3600000,
  "mime_type": "video/mp4",
  "genre_ids": [1, 3]
}
```

| フィールド | 型 | 必須 | 制約 |
|-----------|-----|------|------|
| `title` | string | ○ | 1〜500 文字 |
| `description` | string | - | 任意 |
| `series_id` | int | - | 作品に紐づける場合に指定 |
| `episode_number` | int | - | 1 以上。`series_id` 指定時は推奨 |
| `episode_title` | string | - | 1〜500 文字 |
| `sort_order` | int | - | 0 以上。省略時 `0` |
| `duration_ms` | int | ○ | 1〜14,400,000（最大約 4 時間） |
| `mime_type` | string | - | 省略時 `video/mp4` |
| `genre_ids` | int[] | - | ジャンル ID の配列 |

**レスポンス 201**

```json
{
  "video_id": 100,
  "status": "uploading",
  "title": "第1話 はじまり",
  "chunk_count": 0,
  "created_at": "2026-06-13T10:00:00+09:00"
}
```

**エラー**

| コード | 条件 |
|--------|------|
| 404 | `series_id` または `genre_ids` の ID が存在しない |
| 409 | 同一作品内で `episode_number` が重複 |

**処理概要**

1. `movie.video` に `status = 'uploading'` で INSERT
2. `genre_ids` があれば `movie.video_genre` に INSERT
3. `video_id` を返却

---

### 6.4 動画チャンクアップロード

動画バイナリをチャンク単位で登録する。登録完了後に完了 API を呼ぶ。

```
POST /api/v1/movie/videos/{video_id}/chunks
```

**リクエスト**

`Content-Type: multipart/form-data`

| パート | 型 | 必須 | 説明 |
|--------|-----|------|------|
| `chunk_index` | int | ○ | チャンク連番（0 始まり） |
| `start_time_ms` | int | ○ | チャンク開始時刻（ミリ秒） |
| `end_time_ms` | int | ○ | チャンク終了時刻（ミリ秒） |
| `data` | file | ○ | 動画バイナリ |

**レスポンス 201**

```json
{
  "video_id": 100,
  "chunk_index": 12,
  "byte_length": 524288,
  "uploaded_chunks": 13
}
```

**エラー**

| コード | 条件 |
|--------|------|
| 400 | 時刻範囲不正、空データ |
| 404 | 動画が存在しない |
| 409 | 同一 `chunk_index` が既に登録済み |
| 422 | `status` が `uploading` 以外 |

**処理概要**

1. 所有者チェック
2. `movie.video_chunk` に INSERT
3. `movie.video.chunk_count` と `file_size_bytes` を加算更新

---

### 6.5 動画アップロード完了

全チャンクのアップロード後に呼び出し、再生可能状態にする。

```
POST /api/v1/movie/videos/{video_id}/complete
```

**リクエストボディ**

```json
{
  "duration_ms": 3600000,
  "chunk_count": 720
}
```

| フィールド | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| `duration_ms` | int | ○ | 確定した総再生時間 |
| `chunk_count` | int | ○ | 登録したチャンク総数（整合性検証用） |

**レスポンス 200**

```json
{
  "video_id": 100,
  "status": "ready",
  "duration_ms": 3600000,
  "chunk_count": 720,
  "file_size_bytes": 524288000
}
```

**エラー**

| コード | 条件 |
|--------|------|
| 422 | チャンク数不一致、チャンク未登録 |

**処理概要**

1. DB 上の `chunk_count` とリクエスト値を照合
2. `duration_ms` を更新し `status = 'ready'` に変更

---

### 6.6 動画編集（メタデータのみ）

```
PUT /api/v1/movie/videos/{video_id}
```

**リクエストボディ**（指定したフィールドのみ更新。未指定は変更しない）

```json
{
  "title": "第1話 はじまり（改訂）",
  "description": "説明の更新",
  "series_id": 10,
  "episode_number": 1,
  "episode_title": "はじまり",
  "sort_order": 1,
  "genre_ids": [1, 3]
}
```

| フィールド | 型 | 変更可否 | 説明 |
|-----------|-----|---------|------|
| `title` | string | ○ | タイトル |
| `description` | string | ○ | 説明 |
| `series_id` | int \| null | ○ | 作品の紐づけ変更・解除 |
| `episode_number` | int \| null | ○ | 話数 |
| `episode_title` | string | ○ | 話タイトル |
| `sort_order` | int | ○ | 作品内順序 |
| `genre_ids` | int[] | ○ | ジャンル全置換 |
| `duration_ms` | - | **×** | 変更不可 |
| `mime_type` | - | **×** | 変更不可 |
| チャンク関連 | - | **×** | ファイル入れ替え不可 |

**レスポンス 200** — 更新後の `VideoDetail`

**エラー**

| コード | 条件 |
|--------|------|
| 409 | 話数重複 |

---

### 6.7 動画削除

物理削除を行い、紐づくチャンク・サムネイル・再生状態も連鎖削除する。

```
DELETE /api/v1/movie/videos/{video_id}
```

**レスポンス 204**（ボディなし）

**エラー**

| コード | 条件 |
|--------|------|
| 404 | 動画が存在しない |

**備考**

- 論理削除（`status = 'deleted'`）ではなく DELETE を実行する実装とする（`ON DELETE CASCADE` 利用）。
- アップロード途中（`uploading`）の動画も削除可能。

---

## 7. サムネイル API

### 7.1 サムネイル取得

```
GET /api/v1/movie/videos/{video_id}/thumbnail
```

**レスポンス 200**

- `Content-Type`: 登録時の MIME（通常 `image/jpeg`）
- ボディ: 画像バイナリ

**エラー**

| コード | 条件 |
|--------|------|
| 404 | サムネイル未登録 |

---

### 7.2 サムネイル登録

```
POST /api/v1/movie/videos/{video_id}/thumbnail
```

**リクエスト**

`Content-Type: multipart/form-data`

| パート | 型 | 必須 | 説明 |
|--------|-----|------|------|
| `data` | file | ○ | 画像バイナリ |
| `mime_type` | string | - | 省略時 `image/jpeg` |
| `width` | int | - | 画像幅 |
| `height` | int | - | 画像高さ |

**レスポンス 201**

```json
{
  "video_id": 100,
  "mime_type": "image/jpeg",
  "width": 320,
  "height": 180
}
```

既存サムネイルがある場合は上書き（UPSERT）する。

---

## 8. 再生 API

再生のうち、デコード・描画・早送り・一時停止の制御は **クライアント（ブラウザ）側** で行う。
サーバーは **再生に必要なメタデータ・チャンクデータの配信** と **再生位置の永続化** を担う。

### 8.1 再生開始

再生に必要な情報を取得し、再生回数を記録する。

```
POST /api/v1/movie/videos/{video_id}/playback/start
```

**リクエストボディ**

```json
{
  "resume": true
}
```

| フィールド | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| `resume` | boolean | - | `true`（デフォルト）: 前回位置から再開。`false`: 先頭から再生 |

**レスポンス 200** — `PlaybackInfo` に加え、開始チャンク情報

```json
{
  "video_id": 100,
  "title": "第1話 はじまり",
  "duration_ms": 3600000,
  "mime_type": "video/mp4",
  "chunk_count": 720,
  "position_ms": 120000,
  "completed": false,
  "status": "ready",
  "start_chunk": {
    "chunk_index": 24,
    "start_time_ms": 120000,
    "end_time_ms": 125000,
    "byte_length": 524288
  }
}
```

**処理概要**

1. `status = 'ready'` を確認
2. `resume` に応じて `position_ms` を決定（`false` なら `0`）
3. `position_ms` に対応するチャンクを特定して `start_chunk` に返却
4. `playback_state` の `play_count` を +1、`last_played_at` を更新

**エラー**

| コード | 条件 |
|--------|------|
| 422 | `status` が `ready` 以外 |

---

### 8.2 チャンク一覧取得（メタデータ）

```
GET /api/v1/movie/videos/{video_id}/chunks
```

**レスポンス 200**

```json
{
  "video_id": 100,
  "chunk_count": 720,
  "items": [
    {
      "chunk_index": 0,
      "start_time_ms": 0,
      "end_time_ms": 5000,
      "byte_length": 524288
    }
  ]
}
```

バイナリは含まない。プレイリスト構築・プリフェッチ計画用。

---

### 8.3 チャンクデータ取得（順次再生用）

```
GET /api/v1/movie/videos/{video_id}/chunks/{chunk_index}
```

**レスポンス 200**

- `Content-Type`: 動画の `mime_type`
- ヘッダー例:
  - `X-Chunk-Index: 12`
  - `X-Start-Time-Ms: 60000`
  - `X-End-Time-Ms: 65000`
- ボディ: 動画チャンクバイナリ

**エラー**

| コード | 条件 |
|--------|------|
| 404 | チャンクが存在しない |
| 422 | 動画が再生不可状態 |

---

### 8.4 シーク（指定時間への移動）

指定時刻に対応するチャンクを返す。クライアントは返却チャンクからデコードを再開する。

```
GET /api/v1/movie/videos/{video_id}/playback/seek
```

**クエリパラメータ**

| パラメータ | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| `position_ms` | int | ○ | 移動先の再生位置（ミリ秒） |

**レスポンス 200**

```json
{
  "video_id": 100,
  "position_ms": 600000,
  "chunk": {
    "chunk_index": 120,
    "start_time_ms": 600000,
    "end_time_ms": 605000,
    "byte_length": 524288
  },
  "chunk_url": "/api/v1/movie/videos/100/chunks/120"
}
```

**バリデーション**

- `0 <= position_ms <= duration_ms`

**処理概要**

1. `position_ms` に対応するチャンクを `start_time_ms <= position_ms` で検索
2. クライアントは `chunk_url` からバイナリを取得して再生再開

**備考**

- シーク自体はクライアント側のシークバー操作で即時反映してよい。
- 本 API はシーク先チャンクの特定をサーバーに委譲する場合に使用する。

---

### 8.5 一時停止・再生位置保存

一時停止、シーク完了、タブ閉じる直前等で呼び出し、再生位置を永続化する。

```
PUT /api/v1/movie/videos/{video_id}/playback/state
```

**リクエストボディ**

```json
{
  "position_ms": 125000,
  "completed": false
}
```

| フィールド | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| `position_ms` | int | ○ | 現在の再生位置（ミリ秒） |
| `completed` | boolean | - | 最後まで視聴した場合 `true` |

**レスポンス 200**

```json
{
  "video_id": 100,
  "position_ms": 125000,
  "completed": false,
  "last_played_at": "2026-06-13T15:35:00+09:00"
}
```

**処理概要**

1. `playback_state` を UPSERT
2. `position_ms`・`completed`・`last_played_at` を更新

**備考**

- **一時停止**はクライアント側でメディア再生を停止し、本 API で位置を保存する。
- 再生中の定期保存（例: 10 秒ごと）にも使用可能。

---

### 8.6 再生状態取得

```
GET /api/v1/movie/videos/{video_id}/playback/state
```

**レスポンス 200**

```json
{
  "video_id": 100,
  "position_ms": 125000,
  "completed": false,
  "play_count": 3,
  "last_played_at": "2026-06-13T15:35:00+09:00"
}
```

未視聴の場合:

```json
{
  "video_id": 100,
  "position_ms": 0,
  "completed": false,
  "play_count": 0,
  "last_played_at": null
}
```

---

### 8.7 次の動画取得

同一作品内の次の話、または一覧上の次の動画を取得する。

```
GET /api/v1/movie/videos/{video_id}/next
```

**レスポンス 200**

```json
{
  "has_next": true,
  "video": {
    "video_id": 101,
    "title": "第2話 展開",
    "episode_number": 2,
    "sort_order": 2,
    "duration_ms": 3600000,
    "status": "ready"
  }
}
```

次がない場合:

```json
{
  "has_next": false,
  "video": null
}
```

**取得ロジック**

1. 現在動画に `series_id` がある場合: 同一 `series_id` で `sort_order` が greater の最小 `video_id`（`status = 'ready'`）
2. `series_id` が NULL の場合: 同一ユーザーの `created_at` 順で次の `ready` 動画

---

### 8.8 視聴履歴一覧

```
GET /api/v1/movie/playback/history
```

**クエリパラメータ**

| パラメータ | 型 | 説明 |
|-----------|-----|------|
| `page` | int | ページ番号 |
| `per_page` | int | 件数 |

**レスポンス 200**

```json
{
  "items": [
    {
      "video_id": 100,
      "title": "第1話 はじまり",
      "position_ms": 125000,
      "completed": false,
      "duration_ms": 3600000,
      "last_played_at": "2026-06-13T15:35:00+09:00"
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total_count": 5,
    "total_pages": 1
  }
}
```

`last_played_at` 降順で返す。

---

## 9. 操作と API の対応表

| ユーザー操作 | 主な API | 備考 |
|-------------|---------|------|
| 動画を登録 | `POST /videos` → `POST /chunks` × N → `POST /complete` | チャンク分割アップロード |
| 動画を削除 | `DELETE /videos/{id}` | 物理削除 |
| タイトル・ジャンル等を変更 | `PUT /videos/{id}` | ファイル変更不可 |
| 動画一覧を見る | `GET /videos` | |
| ジャンルで絞り込み | `GET /videos?genre_id=` | |
| ジャンルを追加 | `POST /genres` | ユーザー独自のみ |
| 再生開始 | `POST /playback/start` | 前回位置から再開可 |
| 順次再生 | `GET /chunks/{index}` | 次チャンクを順に取得 |
| 一時停止 | `PUT /playback/state` | クライアント停止 + 位置保存 |
| シーク | `GET /playback/seek?position_ms=` → `GET /chunks/{index}` | クライアントで再生位置変更 |
| 早送り | クライアント側のみ | 停止時に `PUT /playback/state` |
| 次の動画 | `GET /videos/{id}/next` → `POST /playback/start` | |
| サムネイル表示 | `GET /videos/{id}/thumbnail` | |

---

## 10. エンドポイント一覧

| メソッド | パス | 説明 |
|---------|------|------|
| GET | `/genres` | ジャンル一覧 |
| POST | `/genres` | ジャンル追加 |
| GET | `/series` | 作品一覧 |
| POST | `/series` | 作品登録 |
| GET | `/series/{series_id}` | 作品詳細 |
| GET | `/videos` | 動画一覧 |
| POST | `/videos` | 動画登録（メタデータ） |
| GET | `/videos/{video_id}` | 動画詳細 |
| PUT | `/videos/{video_id}` | 動画編集 |
| DELETE | `/videos/{video_id}` | 動画削除 |
| POST | `/videos/{video_id}/chunks` | チャンクアップロード |
| POST | `/videos/{video_id}/complete` | アップロード完了 |
| GET | `/videos/{video_id}/chunks` | チャンク一覧（メタ） |
| GET | `/videos/{video_id}/chunks/{chunk_index}` | チャンクデータ取得 |
| GET | `/videos/{video_id}/thumbnail` | サムネイル取得 |
| POST | `/videos/{video_id}/thumbnail` | サムネイル登録 |
| POST | `/videos/{video_id}/playback/start` | 再生開始 |
| GET | `/videos/{video_id}/playback/seek` | シーク |
| GET | `/videos/{video_id}/playback/state` | 再生状態取得 |
| PUT | `/videos/{video_id}/playback/state` | 再生位置保存（一時停止含む） |
| GET | `/videos/{video_id}/next` | 次の動画 |
| GET | `/playback/history` | 視聴履歴 |

---

## 11. 実装上の注意

### 11.1 セキュリティ

- すべてのエンドポイントでバックエンド取得の `aid` による所有者チェックを実施する。
- チャンク・サムネイルのバイナリは認証必須とする。

### 11.2 パフォーマンス

- チャンク取得は 1 リクエスト 1 チャンクとし、大容量レスポンスのタイムアウトを避ける。
- 一覧 API では `video_chunk.data` を JOIN しない。

### 11.3 クライアント再生

- `video/mp4`（fragmented MP4）を想定し、Media Source Extensions（MSE）でチャンクを連結再生する。
- 早送り・一時停止は HTML5 Video / MSE の API で制御し、サーバーは状態保存のみ行う。

### 11.4 アップロード失敗時

- クライアントは `DELETE /videos/{id}` で中途半端なデータを削除するか、再アップロード前に既存チャンクの重複エラー（409）をハンドリングする。

---

## 12. 改訂履歴

| 版 | 日付 | 内容 |
|----|------|------|
| 1.0 | 2026-06-13 | 初版作成 |
