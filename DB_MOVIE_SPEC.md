# DB テーブル設計仕様書 — 動画視聴アプリ（movie スキーマ）

## 1. 概要

ブラウザ上で動画を再生する Web アプリ向けの PostgreSQL データベース設計。
動画バイナリは DB 内（`BYTEA`）にチャンク分割して保持し、ストリーミング再生・シーク・早送り・次の動画への遷移を実現する。

| 項目 | 内容 |
|------|------|
| DB | PostgreSQL 14+ 推奨 |
| スキーマ名 | `movie` |
| ユーザー識別 | アカウント ID `aid`（`INT`） |
| 動画の最大長 | 約 4 時間（14,400,000 ms） |
| 文字コード | UTF-8 |

### 1.1 設計方針

1. **ユーザー単位のデータ分離** — すべてのユーザー所有データに `aid` を持たせ、他ユーザーのデータへのアクセスを FK・インデックス・アプリ層の WHERE 句で制御する。
2. **メタデータとバイナリの分離** — 再生制御に必要な情報（長さ・話数・順序）は `video` 等のメタデータテーブルに集約し、バイナリは `video_chunk` に分割格納する。
3. **時間ベースのチャンク** — 各チャンクに `start_time_ms` / `end_time_ms` を持たせ、指定時間への移動（シーク）時に必要なチャンクだけを取得できるようにする。
4. **作品・話数管理** — `series`（作品）と `video.episode_number` / `sort_order` でシリーズ再生・「次の動画」遷移を実現する。
5. **ジャンル** — システム共通ジャンルとユーザー独自ジャンルの両方を `genre` で管理し、動画とは多対多で関連付ける。

### 1.2 外部前提

- ユーザーアカウントは別システムで管理されている。
- `aid` は外部のアカウントテーブル（例: `public.account(aid)`）を参照する想定。
- 本仕様ではアカウントテーブル自体は作成しない。SQL 生成時に外部 FK を追加するかは運用方針に応じて判断する。

---

## 2. ER 概要

```
genre ─────┐
           ├──< video_genre >──┐
series ────┤                   │
           │                   video ────< video_chunk
           └───────────────────┤
                               ├──< thumbnail
                               └──< playback_state
```

---

## 3. テーブル一覧

| # | テーブル名 | 説明 |
|---|-----------|------|
| 1 | `movie.genre` | ジャンルマスタ |
| 2 | `movie.series` | 作品（シリーズ） |
| 3 | `movie.video` | 動画メタデータ |
| 4 | `movie.video_genre` | 動画とジャンルの中間テーブル |
| 5 | `movie.video_chunk` | 動画バイナリ（チャンク） |
| 6 | `movie.thumbnail` | サムネイル画像 |
| 7 | `movie.playback_state` | ユーザー別の再生位置・視聴状態 |

---

## 4. テーブル定義

### 4.1 `movie.genre` — ジャンルマスタ

洋画・邦画・ライブ・アニメ等のジャンルを管理する。`aid IS NULL` の行は全ユーザー共通のシステムジャンル、`aid` ありの行はユーザー独自ジャンル。

| カラム名 | 型 | NULL | デフォルト | 説明 |
|----------|-----|------|-----------|------|
| `genre_id` | `SERIAL` | NOT NULL | — | **主キー** |
| `aid` | `INT` | NULL | — | ユーザー ID。NULL のときシステム共通ジャンル |
| `name` | `VARCHAR(100)` | NOT NULL | — | ジャンル名（例: 洋画、邦画、ライブ、アニメ） |
| `sort_order` | `INT` | NOT NULL | `0` | 表示順 |
| `created_at` | `TIMESTAMPTZ` | NOT NULL | `NOW()` | 作成日時 |
| `updated_at` | `TIMESTAMPTZ` | NOT NULL | `NOW()` | 更新日時 |

**主キー**

- `PRIMARY KEY (genre_id)`

**ユニーク制約**

- `UNIQUE (aid, name)` — 同一ユーザー（またはシステム）内でジャンル名の重複を禁止

**CHECK 制約**

- `sort_order >= 0`

**インデックス**

- `idx_genre_aid` ON `(aid)`

---

### 4.2 `movie.series` — 作品（シリーズ）

複数話構成の作品を管理する。単発動画のみの場合は `video.series_id` を NULL にし、本テーブルは使わない。

| カラム名 | 型 | NULL | デフォルト | 説明 |
|----------|-----|------|-----------|------|
| `series_id` | `SERIAL` | NOT NULL | — | **主キー** |
| `aid` | `INT` | NOT NULL | — | 所有者のアカウント ID |
| `title` | `VARCHAR(500)` | NOT NULL | — | 作品タイトル |
| `description` | `TEXT` | NULL | — | 作品説明 |
| `created_at` | `TIMESTAMPTZ` | NOT NULL | `NOW()` | 作成日時 |
| `updated_at` | `TIMESTAMPTZ` | NOT NULL | `NOW()` | 更新日時 |

**主キー**

- `PRIMARY KEY (series_id)`

**インデックス**

- `idx_series_aid` ON `(aid)`
- `idx_series_aid_title` ON `(aid, title)`

---

### 4.3 `movie.video` — 動画メタデータ

動画ファイルのメタ情報を保持する。実体のバイナリは `video_chunk` に格納する。

| カラム名 | 型 | NULL | デフォルト | 説明 |
|----------|-----|------|-----------|------|
| `video_id` | `BIGSERIAL` | NOT NULL | — | **主キー** |
| `aid` | `INT` | NOT NULL | — | 所有者のアカウント ID |
| `series_id` | `INT` | NULL | — | 所属作品 ID。単発動画は NULL |
| `title` | `VARCHAR(500)` | NOT NULL | — | 動画タイトル |
| `description` | `TEXT` | NULL | — | 動画説明 |
| `episode_number` | `INT` | NULL | — | 話数（第1話=1 等）。単発動画は NULL 可 |
| `episode_title` | `VARCHAR(500)` | NULL | — | 話タイトル（例: 「第3話 決戦」） |
| `sort_order` | `INT` | NOT NULL | `0` | 作品内の再生順序。「次の動画」遷移に使用 |
| `duration_ms` | `BIGINT` | NOT NULL | — | 動画の総再生時間（ミリ秒） |
| `mime_type` | `VARCHAR(100)` | NOT NULL | `'video/mp4'` | MIME タイプ |
| `file_size_bytes` | `BIGINT` | NOT NULL | `0` | 全チャンク合計のバイト数 |
| `chunk_count` | `INT` | NOT NULL | `0` | 登録済みチャンク数 |
| `status` | `VARCHAR(20)` | NOT NULL | `'uploading'` | 状態（後述） |
| `created_at` | `TIMESTAMPTZ` | NOT NULL | `NOW()` | 作成日時 |
| `updated_at` | `TIMESTAMPTZ` | NOT NULL | `NOW()` | 更新日時 |

**主キー**

- `PRIMARY KEY (video_id)`

**外部キー**

| カラム | 参照先 | ON DELETE | ON UPDATE |
|--------|--------|-----------|-----------|
| `series_id` | `movie.series(series_id)` | `SET NULL` | `CASCADE` |

**ユニーク制約**

- `UNIQUE (series_id, episode_number)` — 同一作品内で話数の重複を禁止（`series_id` が NULL の行は PostgreSQL では重複可）

**CHECK 制約**

| 制約名（案） | 条件 | 説明 |
|-------------|------|------|
| `chk_video_duration_ms` | `duration_ms > 0 AND duration_ms <= 14400000` | 最大約 4 時間 |
| `chk_video_file_size_bytes` | `file_size_bytes >= 0` | ファイルサイズは 0 以上 |
| `chk_video_chunk_count` | `chunk_count >= 0` | チャンク数は 0 以上 |
| `chk_video_sort_order` | `sort_order >= 0` | 並び順は 0 以上 |
| `chk_video_episode_number` | `episode_number IS NULL OR episode_number > 0` | 話数は正の整数 |
| `chk_video_status` | `status IN ('uploading', 'ready', 'error', 'deleted')` | 状態値の限定 |

**`status` の意味**

| 値 | 説明 |
|----|------|
| `uploading` | チャンクアップロード中 |
| `ready` | 再生可能 |
| `error` | アップロードまたはエンコード失敗 |
| `deleted` | 論理削除 |

**インデックス**

- `idx_video_aid` ON `(aid)`
- `idx_video_series_sort` ON `(series_id, sort_order)` — 次の動画取得用
- `idx_video_aid_status` ON `(aid, status)` — 一覧表示用
- `idx_video_series_episode` ON `(series_id, episode_number)` — 話数検索用

---

### 4.4 `movie.video_genre` — 動画とジャンルの中間テーブル

1 つの動画に複数ジャンルを付与できる（例: 洋画 + ライブ）。

| カラム名 | 型 | NULL | デフォルト | 説明 |
|----------|-----|------|-----------|------|
| `video_id` | `BIGINT` | NOT NULL | — | 動画 ID |
| `genre_id` | `INT` | NOT NULL | — | ジャンル ID |
| `created_at` | `TIMESTAMPTZ` | NOT NULL | `NOW()` | 関連付け日時 |

**主キー**

- `PRIMARY KEY (video_id, genre_id)`

**外部キー**

| カラム | 参照先 | ON DELETE | ON UPDATE |
|--------|--------|-----------|-----------|
| `video_id` | `movie.video(video_id)` | `CASCADE` | `CASCADE` |
| `genre_id` | `movie.genre(genre_id)` | `CASCADE` | `CASCADE` |

**インデックス**

- `idx_video_genre_genre_id` ON `(genre_id)`

---

### 4.5 `movie.video_chunk` — 動画バイナリ（チャンク）

動画データを時間単位で分割して DB 内に保持する。Web アプリはチャンク単位でデータを取得し、Media Source Extensions（MSE）等で再生する。

| カラム名 | 型 | NULL | デフォルト | 説明 |
|----------|-----|------|-----------|------|
| `chunk_id` | `BIGSERIAL` | NOT NULL | — | **主キー** |
| `video_id` | `BIGINT` | NOT NULL | — | 動画 ID |
| `chunk_index` | `INT` | NOT NULL | — | チャンクの連番（0 始まり） |
| `start_time_ms` | `BIGINT` | NOT NULL | — | チャンク開始時刻（ミリ秒） |
| `end_time_ms` | `BIGINT` | NOT NULL | — | チャンク終了時刻（ミリ秒） |
| `byte_length` | `INT` | NOT NULL | — | チャンクのバイト長 |
| `data` | `BYTEA` | NOT NULL | — | 動画バイナリデータ |
| `created_at` | `TIMESTAMPTZ` | NOT NULL | `NOW()` | 作成日時 |

**主キー**

- `PRIMARY KEY (chunk_id)`

**外部キー**

| カラム | 参照先 | ON DELETE | ON UPDATE |
|--------|--------|-----------|-----------|
| `video_id` | `movie.video(video_id)` | `CASCADE` | `CASCADE` |

**ユニーク制約**

- `UNIQUE (video_id, chunk_index)` — 同一動画内でチャンク番号の重複を禁止

**CHECK 制約**

| 制約名（案） | 条件 | 説明 |
|-------------|------|------|
| `chk_video_chunk_index` | `chunk_index >= 0` | チャンク番号は 0 以上 |
| `chk_video_chunk_time` | `start_time_ms >= 0 AND end_time_ms > start_time_ms` | 時間範囲の妥当性 |
| `chk_video_chunk_byte_length` | `byte_length > 0` | 空チャンク禁止 |
| `chk_video_chunk_data_length` | `octet_length(data) = byte_length` | 宣言サイズと実データの一致 |

**インデックス**

- `idx_video_chunk_video_id` ON `(video_id, chunk_index)` — 順次再生用
- `idx_video_chunk_seek` ON `(video_id, start_time_ms)` — シーク（指定時間への移動）用

**チャンク設計の推奨**

| 項目 | 推奨値 |
|------|--------|
| チャンクの時間長 | 2〜10 秒（fMP4 セグメント等） |
| フォーマット | `video/mp4`（fragmented MP4 が MSE と相性良好） |
| 最大チャンクサイズ | アプリ側で 1〜8 MB 程度を目安（`byte_length` で検証） |

---

### 4.6 `movie.thumbnail` — サムネイル画像

動画のポスター画像を DB 内に保持する。1 動画につき 1 サムネイル（必要に応じて将来拡張可）。

| カラム名 | 型 | NULL | デフォルト | 説明 |
|----------|-----|------|-----------|------|
| `thumbnail_id` | `SERIAL` | NOT NULL | — | **主キー** |
| `video_id` | `BIGINT` | NOT NULL | — | 動画 ID |
| `mime_type` | `VARCHAR(50)` | NOT NULL | `'image/jpeg'` | 画像 MIME タイプ |
| `width` | `INT` | NULL | — | 画像幅（px） |
| `height` | `INT` | NULL | — | 画像高さ（px） |
| `data` | `BYTEA` | NOT NULL | — | 画像バイナリ |
| `created_at` | `TIMESTAMPTZ` | NOT NULL | `NOW()` | 作成日時 |

**主キー**

- `PRIMARY KEY (thumbnail_id)`

**外部キー**

| カラム | 参照先 | ON DELETE | ON UPDATE |
|--------|--------|-----------|-----------|
| `video_id` | `movie.video(video_id)` | `CASCADE` | `CASCADE` |

**ユニーク制約**

- `UNIQUE (video_id)` — 1 動画 1 サムネイル

**CHECK 制約**

- `octet_length(data) > 0`

---

### 4.7 `movie.playback_state` — 再生位置・視聴状態

ユーザーごとの再生位置を保持し、途中再開・視聴履歴の管理に使う。早送り・シーク操作の結果もここに保存する。

| カラム名 | 型 | NULL | デフォルト | 説明 |
|----------|-----|------|-----------|------|
| `playback_id` | `BIGSERIAL` | NOT NULL | — | **主キー** |
| `aid` | `INT` | NOT NULL | — | アカウント ID |
| `video_id` | `BIGINT` | NOT NULL | — | 動画 ID |
| `position_ms` | `BIGINT` | NOT NULL | `0` | 最後に停止した再生位置（ミリ秒） |
| `completed` | `BOOLEAN` | NOT NULL | `FALSE` | 最後まで視聴完了したか |
| `play_count` | `INT` | NOT NULL | `0` | 再生回数 |
| `last_played_at` | `TIMESTAMPTZ` | NOT NULL | `NOW()` | 最終再生日時 |
| `created_at` | `TIMESTAMPTZ` | NOT NULL | `NOW()` | 作成日時 |
| `updated_at` | `TIMESTAMPTZ` | NOT NULL | `NOW()` | 更新日時 |

**主キー**

- `PRIMARY KEY (playback_id)`

**外部キー**

| カラム | 参照先 | ON DELETE | ON UPDATE |
|--------|--------|-----------|-----------|
| `video_id` | `movie.video(video_id)` | `CASCADE` | `CASCADE` |

**ユニーク制約**

- `UNIQUE (aid, video_id)` — ユーザー×動画で 1 レコード

**CHECK 制約**

| 制約名（案） | 条件 | 説明 |
|-------------|------|------|
| `chk_playback_position_ms` | `position_ms >= 0` | 再生位置は 0 以上 |
| `chk_playback_play_count` | `play_count >= 0` | 再生回数は 0 以上 |

**インデックス**

- `idx_playback_aid_last_played` ON `(aid, last_played_at DESC)` — 視聴履歴一覧用
- `idx_playback_video_id` ON `(video_id)`

---

## 5. 再生機能とテーブルの対応

| 操作 | 使用テーブル・カラム | 取得・更新の概要 |
|------|---------------------|-----------------|
| 再生開始 | `video`, `video_chunk`, `playback_state` | `status = 'ready'` を確認。`chunk_index = 0` から順に `data` を取得して再生。`playback_state.position_ms` から途中再開も可 |
| 早送り | `video_chunk` | クライアント側でデコード位置を進める。DB への書き込みは不要（停止時に `playback_state` を更新） |
| 指定時間への移動（シーク） | `video_chunk` | `WHERE video_id = ? AND start_time_ms <= ? ORDER BY start_time_ms DESC LIMIT 1` で対象チャンクを特定し、そのチャンクからデコード開始 |
| 途中再開 | `playback_state` | `position_ms` を読み取り、上記シークと同様にチャンクを取得 |
| 次の動画へ | `video` | 同一 `series_id` 内で `sort_order`（または `episode_number`）が現在より大きい最小の `video_id` を取得。単発動画は `aid` 内の `created_at` 順等で代替可能 |
| ジャンル別一覧 | `video`, `video_genre`, `genre` | `genre.name` でフィルタ |
| 話数指定再生 | `video` | `series_id` + `episode_number` で特定 |

### 5.1 「次の動画」取得クエリ（参考）

```sql
-- 現在の動画の次の話を取得
SELECT v.*
FROM movie.video AS cur
JOIN movie.video AS v
  ON v.series_id = cur.series_id
 AND v.sort_order > cur.sort_order
 AND v.status = 'ready'
WHERE cur.video_id = :current_video_id
  AND cur.aid = :aid
ORDER BY v.sort_order ASC
LIMIT 1;
```

---

## 6. 初期データ（システムジャンル）

SQL 生成時に以下のマスタを `INSERT` する想定（`aid IS NULL`）。

| name | sort_order |
|------|-----------|
| 洋画 | 1 |
| 邦画 | 2 |
| アニメ | 3 |
| ライブ | 4 |
| ドラマ | 5 |
| ドキュメンタリー | 6 |
| その他 | 99 |

---

## 7. 運用上の注意

### 7.1 大容量データ

- 4 時間の動画を単一 `BYTEA` に格納せず、必ず `video_chunk` に分割する。
- `BYTEA` の TOAST 圧縮が自動適用されるが、チャンクサイズを抑えることでシーク応答性が向上する。
- 接続タイムアウト対策として、チャンク取得は 1 件ずつストリーミング返却する API 設計を推奨。

### 7.2 トランザクション

- チャンクの一括 INSERT 完了後に `video.chunk_count`・`video.file_size_bytes`・`video.duration_ms` を更新し、`status` を `ready` にする。
- アップロード失敗時は `status = 'error'` とし、不完全な `video_chunk` は削除する。

### 7.3 セキュリティ

- すべての SELECT / UPDATE / DELETE に `aid` による所有者チェックを必須とする。
- `video_chunk.data` は直接 URL 公開せず、認証済み API 経由でのみ返却する。

### 7.4 将来拡張（本仕様の範囲外・参考）

| 機能 | 追加テーブル案 |
|------|---------------|
| お気に入り | `movie.favorite(aid, video_id)` |
| カスタムプレイリスト | `movie.playlist`, `movie.playlist_item` |
| 字幕 | `movie.subtitle(video_id, language, data)` |
| キーフレーム索引（高精度シーク） | `movie.video_keyframe(video_id, time_ms, chunk_id, byte_offset)` |

---

## 8. テーブル定義サマリ（SQL 生成用）

```
SCHEMA: movie

TABLE movie.genre
  PK: genre_id
  UNIQUE: (aid, name)

TABLE movie.series
  PK: series_id

TABLE movie.video
  PK: video_id
  FK: series_id → movie.series(series_id) ON DELETE SET NULL
  UNIQUE: (series_id, episode_number)

TABLE movie.video_genre
  PK: (video_id, genre_id)
  FK: video_id → movie.video(video_id) ON DELETE CASCADE
  FK: genre_id → movie.genre(genre_id) ON DELETE CASCADE

TABLE movie.video_chunk
  PK: chunk_id
  FK: video_id → movie.video(video_id) ON DELETE CASCADE
  UNIQUE: (video_id, chunk_index)

TABLE movie.thumbnail
  PK: thumbnail_id
  FK: video_id → movie.video(video_id) ON DELETE CASCADE
  UNIQUE: (video_id)

TABLE movie.playback_state
  PK: playback_id
  FK: video_id → movie.video(video_id) ON DELETE CASCADE
  UNIQUE: (aid, video_id)
```

---

## 9. 改訂履歴

| 版 | 日付 | 内容 |
|----|------|------|
| 1.0 | 2026-06-13 | 初版作成 |
