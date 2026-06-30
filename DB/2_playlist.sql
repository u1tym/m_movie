-- =============================================================================
-- プレイリスト・再生コンテキスト — テーブル追加 SQL
-- 前提: DB/1_db.sql 実行済み
-- =============================================================================

BEGIN;

-- -----------------------------------------------------------------------------
-- 1. movie.playlist — プレイリスト
-- -----------------------------------------------------------------------------
CREATE TABLE movie.playlist (
    playlist_id   SERIAL          NOT NULL,
    aid           INT             NOT NULL,
    name          VARCHAR(500)    NOT NULL,
    description   TEXT            NULL,
    created_at    TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT pk_playlist PRIMARY KEY (playlist_id),
    CONSTRAINT fk_playlist_aid FOREIGN KEY (aid)
        REFERENCES public.accounts (id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);

CREATE INDEX idx_playlist_aid ON movie.playlist (aid);

COMMENT ON TABLE movie.playlist IS 'ユーザ独自プレイリスト';

-- -----------------------------------------------------------------------------
-- 2. movie.playlist_item — プレイリスト内の動画（同一動画の重複可）
-- -----------------------------------------------------------------------------
CREATE TABLE movie.playlist_item (
    playlist_item_id  BIGSERIAL       NOT NULL,
    playlist_id       INT             NOT NULL,
    video_id          BIGINT          NOT NULL,
    sort_order        INT             NOT NULL,
    created_at        TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT pk_playlist_item PRIMARY KEY (playlist_item_id),
    CONSTRAINT uq_playlist_item_sort UNIQUE (playlist_id, sort_order),
    CONSTRAINT chk_playlist_item_sort_order CHECK (sort_order >= 0),
    CONSTRAINT fk_playlist_item_playlist_id FOREIGN KEY (playlist_id)
        REFERENCES movie.playlist (playlist_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    CONSTRAINT fk_playlist_item_video_id FOREIGN KEY (video_id)
        REFERENCES movie.video (video_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);

CREATE INDEX idx_playlist_item_playlist ON movie.playlist_item (playlist_id, sort_order);
CREATE INDEX idx_playlist_item_video ON movie.playlist_item (video_id);

COMMENT ON TABLE movie.playlist_item IS 'プレイリスト内動画（並び順）';

-- -----------------------------------------------------------------------------
-- 3. movie.playback_context — 最後の再生コンテキスト（単体動画 / プレイリスト）
-- -----------------------------------------------------------------------------
CREATE TABLE movie.playback_context (
    aid                       INT             NOT NULL,
    last_video_id             BIGINT          NULL,
    last_video_position_ms    BIGINT          NOT NULL DEFAULT 0,
    last_video_updated_at     TIMESTAMPTZ     NULL,
    last_playlist_id          INT             NULL,
    last_playlist_item_id     BIGINT          NULL,
    last_playlist_position_ms BIGINT          NOT NULL DEFAULT 0,
    last_playlist_updated_at  TIMESTAMPTZ     NULL,
    updated_at                TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT pk_playback_context PRIMARY KEY (aid),
    CONSTRAINT chk_playback_context_video_position CHECK (last_video_position_ms >= 0),
    CONSTRAINT chk_playback_context_playlist_position CHECK (last_playlist_position_ms >= 0),
    CONSTRAINT fk_playback_context_aid FOREIGN KEY (aid)
        REFERENCES public.accounts (id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    CONSTRAINT fk_playback_context_video_id FOREIGN KEY (last_video_id)
        REFERENCES movie.video (video_id)
        ON DELETE SET NULL
        ON UPDATE CASCADE,
    CONSTRAINT fk_playback_context_playlist_id FOREIGN KEY (last_playlist_id)
        REFERENCES movie.playlist (playlist_id)
        ON DELETE SET NULL
        ON UPDATE CASCADE,
    CONSTRAINT fk_playback_context_playlist_item_id FOREIGN KEY (last_playlist_item_id)
        REFERENCES movie.playlist_item (playlist_item_id)
        ON DELETE SET NULL
        ON UPDATE CASCADE
);

COMMENT ON TABLE movie.playback_context IS '単体動画・プレイリストそれぞれの最終再生位置';

COMMIT;
