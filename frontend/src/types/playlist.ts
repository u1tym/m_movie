export interface PlaylistSummary {
  playlist_id: number
  name: string
  description: string | null
  item_count: number
  created_at: string
  updated_at: string
}

export interface PlaylistItem {
  playlist_item_id: number
  video_id: number
  title: string
  duration_ms: number
  status: string
  sort_order: number
  has_thumbnail: boolean
}

export interface PlaylistDetail {
  playlist_id: number
  name: string
  description: string | null
  items: PlaylistItem[]
  created_at: string
  updated_at: string
}

export interface PlaylistPlaybackItem {
  playlist_id: number
  playlist_item_id: number
  video_id: number
  title: string
  duration_ms: number
  mime_type: string
  chunk_count: number
  position_ms: number
  status: string
  sort_order: number
  stream_token: string
  start_chunk: {
    chunk_index: number
    start_time_ms: number
    end_time_ms: number
    byte_length: number
  }
  has_next: boolean
  has_prev: boolean
}

export interface LastVideoContext {
  video_id: number
  title: string
  duration_ms: number
  position_ms: number
  updated_at: string
}

export interface LastPlaylistContext {
  playlist_id: number
  playlist_name: string
  playlist_item_id: number
  video_id: number
  video_title: string
  duration_ms: number
  position_ms: number
  updated_at: string
}

export interface LastPlayback {
  video: LastVideoContext | null
  playlist: LastPlaylistContext | null
}
