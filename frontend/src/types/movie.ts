export interface Genre {
  genre_id: number
  name: string
  sort_order: number
  is_system: boolean
}

export interface GenreBrief {
  genre_id: number
  name: string
}

export interface Series {
  series_id: number
  title: string
  description: string | null
  created_at: string
  updated_at: string
}

export interface SeriesVideoBrief {
  video_id: number
  episode_number: number | null
  episode_title: string | null
  sort_order: number
  duration_ms: number
  status: string
}

export interface SeriesDetail extends Series {
  videos: SeriesVideoBrief[]
}

export interface VideoSummary {
  video_id: number
  title: string
  description: string | null
  series_id: number | null
  series_title: string | null
  episode_number: number | null
  episode_title: string | null
  sort_order: number
  duration_ms: number
  mime_type: string
  file_size_bytes: number
  status: string
  genres: GenreBrief[]
  has_thumbnail: boolean
  position_ms: number | null
  completed: boolean
  created_at: string
  updated_at: string
}

export interface VideoDetail extends VideoSummary {
  chunk_count: number
  last_played_at: string | null
  play_count: number
}

export interface Pagination {
  page: number
  per_page: number
  total_count: number
  total_pages: number
}

export interface Paginated<T> {
  items: T[]
  pagination: Pagination
}

export interface ItemsResponse<T> {
  items: T[]
}

export interface VideoCreatePayload {
  title: string
  description?: string | null
  series_id?: number | null
  episode_number?: number | null
  episode_title?: string | null
  sort_order?: number
  duration_ms: number
  mime_type?: string
  genre_ids?: number[]
}

export interface VideoUpdatePayload {
  title?: string
  description?: string | null
  series_id?: number | null
  episode_number?: number | null
  episode_title?: string | null
  sort_order?: number
  genre_ids?: number[]
}

export interface ChunkMeta {
  chunk_index: number
  start_time_ms: number
  end_time_ms: number
  byte_length: number
}

export interface PlaybackStartResponse {
  video_id: number
  title: string
  duration_ms: number
  mime_type: string
  chunk_count: number
  position_ms: number
  completed: boolean
  status: string
  start_chunk: ChunkMeta
}

export interface PlaybackState {
  video_id: number
  position_ms: number
  completed: boolean
  play_count: number
  last_played_at: string | null
}

export interface NextVideoBrief {
  video_id: number
  title: string
  episode_number: number | null
  sort_order: number
  duration_ms: number
  status: string
}

export interface NextVideoResponse {
  has_next: boolean
  video: NextVideoBrief | null
}

export interface VideoListParams {
  page?: number
  per_page?: number
  genre_id?: number
  series_id?: number
  status?: string
  q?: string
  sort?: string
  order?: string
}

export interface SeriesCreatePayload {
  title: string
  description?: string | null
}
