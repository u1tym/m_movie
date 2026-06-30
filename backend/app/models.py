from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, LargeBinary, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Genre(Base):
    __tablename__ = "genre"
    __table_args__ = {"schema": "movie"}

    genre_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    aid: Mapped[int | None] = mapped_column(Integer, nullable=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Series(Base):
    __tablename__ = "series"
    __table_args__ = {"schema": "movie"}

    series_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    aid: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    videos: Mapped[list["Video"]] = relationship(back_populates="series")


class Video(Base):
    __tablename__ = "video"
    __table_args__ = {"schema": "movie"}

    video_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    aid: Mapped[int] = mapped_column(Integer, nullable=False)
    series_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("movie.series.series_id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    episode_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    episode_title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duration_ms: Mapped[int] = mapped_column(BigInteger, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False, default="video/mp4")
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="uploading")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    series: Mapped[Series | None] = relationship(back_populates="videos")
    genres: Mapped[list["VideoGenre"]] = relationship(back_populates="video", cascade="all, delete-orphan")
    chunks: Mapped[list["VideoChunk"]] = relationship(back_populates="video", cascade="all, delete-orphan")
    thumbnail: Mapped["Thumbnail | None"] = relationship(back_populates="video", cascade="all, delete-orphan")
    playback_states: Mapped[list["PlaybackState"]] = relationship(
        back_populates="video", cascade="all, delete-orphan"
    )
    playlist_items: Mapped[list["PlaylistItem"]] = relationship(back_populates="video")


class Playlist(Base):
    __tablename__ = "playlist"
    __table_args__ = {"schema": "movie"}

    playlist_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    aid: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    items: Mapped[list["PlaylistItem"]] = relationship(
        back_populates="playlist", cascade="all, delete-orphan", order_by="PlaylistItem.sort_order"
    )


class PlaylistItem(Base):
    __tablename__ = "playlist_item"
    __table_args__ = {"schema": "movie"}

    playlist_item_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    playlist_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("movie.playlist.playlist_id", ondelete="CASCADE"), nullable=False
    )
    video_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("movie.video.video_id", ondelete="CASCADE"), nullable=False
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    playlist: Mapped[Playlist] = relationship(back_populates="items")
    video: Mapped[Video] = relationship(back_populates="playlist_items")


class PlaybackContext(Base):
    __tablename__ = "playback_context"
    __table_args__ = {"schema": "movie"}

    aid: Mapped[int] = mapped_column(Integer, primary_key=True)
    last_video_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("movie.video.video_id", ondelete="SET NULL"), nullable=True
    )
    last_video_position_ms: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    last_video_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_playlist_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("movie.playlist.playlist_id", ondelete="SET NULL"), nullable=True
    )
    last_playlist_item_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("movie.playlist_item.playlist_item_id", ondelete="SET NULL"), nullable=True
    )
    last_playlist_position_ms: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    last_playlist_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    last_video: Mapped[Video | None] = relationship(foreign_keys=[last_video_id])
    last_playlist: Mapped[Playlist | None] = relationship(foreign_keys=[last_playlist_id])
    last_playlist_item: Mapped[PlaylistItem | None] = relationship(foreign_keys=[last_playlist_item_id])


class VideoGenre(Base):
    __tablename__ = "video_genre"
    __table_args__ = {"schema": "movie"}

    video_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("movie.video.video_id", ondelete="CASCADE"), primary_key=True
    )
    genre_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("movie.genre.genre_id", ondelete="CASCADE"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    video: Mapped[Video] = relationship(back_populates="genres")
    genre: Mapped[Genre] = relationship()


class VideoChunk(Base):
    __tablename__ = "video_chunk"
    __table_args__ = {"schema": "movie"}

    chunk_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    video_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("movie.video.video_id", ondelete="CASCADE"), nullable=False
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    start_time_ms: Mapped[int] = mapped_column(BigInteger, nullable=False)
    end_time_ms: Mapped[int] = mapped_column(BigInteger, nullable=False)
    byte_length: Mapped[int] = mapped_column(Integer, nullable=False)
    data: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    video: Mapped[Video] = relationship(back_populates="chunks")


class Thumbnail(Base):
    __tablename__ = "thumbnail"
    __table_args__ = {"schema": "movie"}

    thumbnail_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    video_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("movie.video.video_id", ondelete="CASCADE"), nullable=False, unique=True
    )
    mime_type: Mapped[str] = mapped_column(String(50), nullable=False, default="image/jpeg")
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    data: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    video: Mapped[Video] = relationship(back_populates="thumbnail")


class PlaybackState(Base):
    __tablename__ = "playback_state"
    __table_args__ = {"schema": "movie"}

    playback_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    aid: Mapped[int] = mapped_column(Integer, nullable=False)
    video_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("movie.video.video_id", ondelete="CASCADE"), nullable=False
    )
    position_ms: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    play_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_played_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    video: Mapped[Video] = relationship(back_populates="playback_states")
