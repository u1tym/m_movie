-- =============================================================================
-- 動画視聴アプリ — テーブル作成 SQL
-- スキーマ: movie
-- 前提: public.accounts テーブルが既に存在すること
-- 仕様: DB_MOVIE_SPEC.md
-- =============================================================================

BEGIN;

-- -----------------------------------------------------------------------------
-- スキーマ
-- -----------------------------------------------------------------------------
CREATE SCHEMA IF NOT EXISTS movie;

-- -----------------------------------------------------------------------------
-- 1. movie.genre — ジャンルマスタ
-- -----------------------------------------------------------------------------
CREATE TABLE movie.genre (
    genre_id    SERIAL          NOT NULL,
    aid         INT             NULL,
    name        VARCHAR(100)    NOT NULL,
    sort_order  INT             NOT NULL DEFAULT 0,
    created_at  TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT pk_genre PRIMARY KEY (genre_id),
    CONSTRAINT uq_genre_aid_name UNIQUE (aid, name),
    CONSTRAINT chk_genre_sort_order CHECK (sort_order >= 0),
    CONSTRAINT fk_genre_aid FOREIGN KEY (aid)
        REFERENCES public.accounts (id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);

CREATE INDEX idx_genre_aid ON movie.genre (aid);

COMMENT ON TABLE  movie.genre            IS 'ジャンルマスタ（aid NULL はシステム共通）';
COMMENT ON COLUMN movie.genre.aid        IS 'アカウント ID。NULL のときシステム共通ジャンル';
COMMENT ON COLUMN movie.genre.name       IS 'ジャンル名（例: 洋画、邦画、ライブ、アニメ）';
COMMENT ON COLUMN movie.genre.sort_order IS '表示順';

-- -----------------------------------------------------------------------------
-- 2. movie.series — 作品（シリーズ）
-- -----------------------------------------------------------------------------
CREATE TABLE movie.series (
    series_id   SERIAL          NOT NULL,
    aid         INT             NOT NULL,
    title       VARCHAR(500)    NOT NULL,
    description TEXT            NULL,
    created_at  TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT pk_series PRIMARY KEY (series_id),
    CONSTRAINT fk_series_aid FOREIGN KEY (aid)
        REFERENCES public.accounts (id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);

CREATE INDEX idx_series_aid ON movie.series (aid);
CREATE INDEX idx_series_aid_title ON movie.series (aid, title);

COMMENT ON TABLE  movie.series       IS '作品（シリーズ）';
COMMENT ON COLUMN movie.series.aid   IS '所有者のアカウント ID';
COMMENT ON COLUMN movie.series.title IS '作品タイトル';

-- -----------------------------------------------------------------------------
-- 3. movie.video — 動画メタデータ
-- -----------------------------------------------------------------------------
CREATE TABLE movie.video (
    video_id        BIGSERIAL       NOT NULL,
    aid             INT             NOT NULL,
    series_id       INT             NULL,
    title           VARCHAR(500)    NOT NULL,
    description     TEXT            NULL,
    episode_number  INT             NULL,
    episode_title   VARCHAR(500)    NULL,
    sort_order      INT             NOT NULL DEFAULT 0,
    duration_ms     BIGINT          NOT NULL,
    mime_type       VARCHAR(100)    NOT NULL DEFAULT 'video/mp4',
    file_size_bytes BIGINT          NOT NULL DEFAULT 0,
    chunk_count     INT             NOT NULL DEFAULT 0,
    status          VARCHAR(20)     NOT NULL DEFAULT 'uploading',
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT pk_video PRIMARY KEY (video_id),
    CONSTRAINT uq_video_series_episode UNIQUE (series_id, episode_number),
    CONSTRAINT chk_video_duration_ms CHECK (duration_ms > 0 AND duration_ms <= 14400000),
    CONSTRAINT chk_video_file_size_bytes CHECK (file_size_bytes >= 0),
    CONSTRAINT chk_video_chunk_count CHECK (chunk_count >= 0),
    CONSTRAINT chk_video_sort_order CHECK (sort_order >= 0),
    CONSTRAINT chk_video_episode_number CHECK (episode_number IS NULL OR episode_number > 0),
    CONSTRAINT chk_video_status CHECK (status IN ('uploading', 'ready', 'error', 'deleted')),
    CONSTRAINT fk_video_aid FOREIGN KEY (aid)
        REFERENCES public.accounts (id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    CONSTRAINT fk_video_series_id FOREIGN KEY (series_id)
        REFERENCES movie.series (series_id)
        ON DELETE SET NULL
        ON UPDATE CASCADE
);

CREATE INDEX idx_video_aid ON movie.video (aid);
CREATE INDEX idx_video_series_sort ON movie.video (series_id, sort_order);
CREATE INDEX idx_video_aid_status ON movie.video (aid, status);
CREATE INDEX idx_video_series_episode ON movie.video (series_id, episode_number);

COMMENT ON TABLE  movie.video                  IS '動画メタデータ';
COMMENT ON COLUMN movie.video.aid              IS '所有者のアカウント ID';
COMMENT ON COLUMN movie.video.series_id        IS '所属作品 ID。単発動画は NULL';
COMMENT ON COLUMN movie.video.episode_number   IS '話数（第1話=1 等）';
COMMENT ON COLUMN movie.video.sort_order       IS '作品内の再生順序（次の動画遷移に使用）';
COMMENT ON COLUMN movie.video.duration_ms      IS '動画の総再生時間（ミリ秒）。最大約4時間';
COMMENT ON COLUMN movie.video.status           IS 'uploading / ready / error / deleted';

-- -----------------------------------------------------------------------------
-- 4. movie.video_genre — 動画とジャンルの中間テーブル
-- -----------------------------------------------------------------------------
CREATE TABLE movie.video_genre (
    video_id    BIGINT          NOT NULL,
    genre_id    INT             NOT NULL,
    created_at  TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT pk_video_genre PRIMARY KEY (video_id, genre_id),
    CONSTRAINT fk_video_genre_video_id FOREIGN KEY (video_id)
        REFERENCES movie.video (video_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    CONSTRAINT fk_video_genre_genre_id FOREIGN KEY (genre_id)
        REFERENCES movie.genre (genre_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);

CREATE INDEX idx_video_genre_genre_id ON movie.video_genre (genre_id);

COMMENT ON TABLE movie.video_genre IS '動画とジャンルの関連';

-- -----------------------------------------------------------------------------
-- 5. movie.video_chunk — 動画バイナリ（チャンク）
-- -----------------------------------------------------------------------------
CREATE TABLE movie.video_chunk (
    chunk_id        BIGSERIAL       NOT NULL,
    video_id        BIGINT          NOT NULL,
    chunk_index     INT             NOT NULL,
    start_time_ms   BIGINT          NOT NULL,
    end_time_ms     BIGINT          NOT NULL,
    byte_length     INT             NOT NULL,
    data            BYTEA           NOT NULL,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT pk_video_chunk PRIMARY KEY (chunk_id),
    CONSTRAINT uq_video_chunk_video_index UNIQUE (video_id, chunk_index),
    CONSTRAINT chk_video_chunk_index CHECK (chunk_index >= 0),
    CONSTRAINT chk_video_chunk_time CHECK (start_time_ms >= 0 AND end_time_ms > start_time_ms),
    CONSTRAINT chk_video_chunk_byte_length CHECK (byte_length > 0),
    CONSTRAINT chk_video_chunk_data_length CHECK (octet_length(data) = byte_length),
    CONSTRAINT fk_video_chunk_video_id FOREIGN KEY (video_id)
        REFERENCES movie.video (video_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);

CREATE INDEX idx_video_chunk_video_id ON movie.video_chunk (video_id, chunk_index);
CREATE INDEX idx_video_chunk_seek ON movie.video_chunk (video_id, start_time_ms);

COMMENT ON TABLE  movie.video_chunk                IS '動画バイナリ（時間単位チャンク）';
COMMENT ON COLUMN movie.video_chunk.chunk_index    IS 'チャンク連番（0 始まり）';
COMMENT ON COLUMN movie.video_chunk.start_time_ms  IS 'チャンク開始時刻（ミリ秒）';
COMMENT ON COLUMN movie.video_chunk.end_time_ms    IS 'チャンク終了時刻（ミリ秒）';
COMMENT ON COLUMN movie.video_chunk.data           IS '動画バイナリデータ';

-- -----------------------------------------------------------------------------
-- 6. movie.thumbnail — サムネイル画像
-- -----------------------------------------------------------------------------
CREATE TABLE movie.thumbnail (
    thumbnail_id    SERIAL          NOT NULL,
    video_id        BIGINT          NOT NULL,
    mime_type       VARCHAR(50)     NOT NULL DEFAULT 'image/jpeg',
    width           INT             NULL,
    height          INT             NULL,
    data            BYTEA           NOT NULL,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT pk_thumbnail PRIMARY KEY (thumbnail_id),
    CONSTRAINT uq_thumbnail_video_id UNIQUE (video_id),
    CONSTRAINT chk_thumbnail_data CHECK (octet_length(data) > 0),
    CONSTRAINT fk_thumbnail_video_id FOREIGN KEY (video_id)
        REFERENCES movie.video (video_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);

COMMENT ON TABLE movie.thumbnail IS '動画サムネイル（1 動画 1 件）';

-- -----------------------------------------------------------------------------
-- 7. movie.playback_state — 再生位置・視聴状態
-- -----------------------------------------------------------------------------
CREATE TABLE movie.playback_state (
    playback_id     BIGSERIAL       NOT NULL,
    aid             INT             NOT NULL,
    video_id        BIGINT          NOT NULL,
    position_ms     BIGINT          NOT NULL DEFAULT 0,
    completed       BOOLEAN         NOT NULL DEFAULT FALSE,
    play_count      INT             NOT NULL DEFAULT 0,
    last_played_at  TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT pk_playback_state PRIMARY KEY (playback_id),
    CONSTRAINT uq_playback_state_aid_video UNIQUE (aid, video_id),
    CONSTRAINT chk_playback_position_ms CHECK (position_ms >= 0),
    CONSTRAINT chk_playback_play_count CHECK (play_count >= 0),
    CONSTRAINT fk_playback_state_aid FOREIGN KEY (aid)
        REFERENCES public.accounts (id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    CONSTRAINT fk_playback_state_video_id FOREIGN KEY (video_id)
        REFERENCES movie.video (video_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);

CREATE INDEX idx_playback_aid_last_played ON movie.playback_state (aid, last_played_at DESC);
CREATE INDEX idx_playback_video_id ON movie.playback_state (video_id);

COMMENT ON TABLE  movie.playback_state              IS 'ユーザー別の再生位置・視聴状態';
COMMENT ON COLUMN movie.playback_state.position_ms  IS '最後に停止した再生位置（ミリ秒）';
COMMENT ON COLUMN movie.playback_state.completed    IS '最後まで視聴完了したか';
COMMENT ON COLUMN movie.playback_state.play_count   IS '再生回数';

-- -----------------------------------------------------------------------------
-- 初期データ: システムジャンル（aid IS NULL）
-- -----------------------------------------------------------------------------
INSERT INTO movie.genre (aid, name, sort_order) VALUES
    (NULL, '洋画',           1),
    (NULL, '邦画',           2),
    (NULL, 'アニメ',         3),
    (NULL, 'ライブ',         4),
    (NULL, 'ドラマ',         5),
    (NULL, 'ドキュメンタリー', 6),
    (NULL, 'その他',         99);

COMMIT;
