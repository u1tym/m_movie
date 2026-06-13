import type {
  ChunkMeta,
  Genre,
  ItemsResponse,
  NextVideoResponse,
  Paginated,
  PlaybackStartResponse,
  PlaybackState,
  Series,
  SeriesCreatePayload,
  SeriesDetail,
  VideoCreatePayload,
  VideoDetail,
  VideoListParams,
  VideoSummary,
  VideoUpdatePayload,
} from '../types/movie'
import { movieFetchBlob, movieRequest } from './client'

// --- Genres ---

export const fetchGenres = (): Promise<ItemsResponse<Genre>> =>
  movieRequest('/genres')

export const createGenre = (body: {
  name: string
  sort_order?: number
}): Promise<Genre> =>
  movieRequest('/genres', { method: 'POST', body: JSON.stringify(body) })

// --- Series ---

export const fetchSeries = (
  page = 1,
  perPage = 50,
  q?: string,
): Promise<Paginated<Series>> =>
  movieRequest('/series', undefined, { page, per_page: perPage, q })

export const createSeries = (body: SeriesCreatePayload): Promise<Series> =>
  movieRequest('/series', { method: 'POST', body: JSON.stringify(body) })

export const fetchSeriesDetail = (seriesId: number): Promise<SeriesDetail> =>
  movieRequest(`/series/${seriesId}`)

// --- Videos ---

export const fetchVideos = (
  params: VideoListParams,
): Promise<Paginated<VideoSummary>> =>
  movieRequest('/videos', undefined, params as Record<string, string | number | undefined>)

export const fetchVideo = (videoId: number): Promise<VideoDetail> =>
  movieRequest(`/videos/${videoId}`)

export const createVideo = (body: VideoCreatePayload): Promise<{
  video_id: number
  status: string
  title: string
  chunk_count: number
  created_at: string
}> => movieRequest('/videos', { method: 'POST', body: JSON.stringify(body) })

export const updateVideo = (
  videoId: number,
  body: VideoUpdatePayload,
): Promise<VideoDetail> =>
  movieRequest(`/videos/${videoId}`, { method: 'PUT', body: JSON.stringify(body) })

export const deleteVideo = (videoId: number): Promise<void> =>
  movieRequest(`/videos/${videoId}`, { method: 'DELETE' })

export const uploadChunk = (
  videoId: number,
  chunkIndex: number,
  startTimeMs: number,
  endTimeMs: number,
  data: Blob,
): Promise<{ video_id: number; chunk_index: number; byte_length: number; uploaded_chunks: number }> => {
  const form = new FormData()
  form.append('chunk_index', String(chunkIndex))
  form.append('start_time_ms', String(startTimeMs))
  form.append('end_time_ms', String(endTimeMs))
  form.append('data', data, `chunk_${chunkIndex}`)
  return movieRequest(`/videos/${videoId}/chunks`, { method: 'POST', body: form })
}

export const completeUpload = (
  videoId: number,
  durationMs: number,
  chunkCount: number,
): Promise<{
  video_id: number
  status: string
  duration_ms: number
  chunk_count: number
  file_size_bytes: number
}> =>
  movieRequest(`/videos/${videoId}/complete`, {
    method: 'POST',
    body: JSON.stringify({ duration_ms: durationMs, chunk_count: chunkCount }),
  })

export const fetchChunkList = (
  videoId: number,
): Promise<{ video_id: number; chunk_count: number; items: ChunkMeta[] }> =>
  movieRequest(`/videos/${videoId}/chunks`)

export const fetchChunkBlob = (videoId: number, chunkIndex: number): Promise<Blob> =>
  movieFetchBlob(`/videos/${videoId}/chunks/${chunkIndex}`)

export const fetchThumbnailBlob = (videoId: number): Promise<Blob> =>
  movieFetchBlob(`/videos/${videoId}/thumbnail`)

export const uploadThumbnail = (
  videoId: number,
  data: Blob,
  mimeType = 'image/jpeg',
): Promise<{ video_id: number; mime_type: string; width: number | null; height: number | null }> => {
  const form = new FormData()
  form.append('data', data, 'thumbnail.jpg')
  form.append('mime_type', mimeType)
  return movieRequest(`/videos/${videoId}/thumbnail`, { method: 'POST', body: form })
}

// --- Playback ---

export const startPlayback = (
  videoId: number,
  resume = true,
): Promise<PlaybackStartResponse> =>
  movieRequest(`/videos/${videoId}/playback/start`, {
    method: 'POST',
    body: JSON.stringify({ resume }),
  })

export const seekPlayback = (
  videoId: number,
  positionMs: number,
): Promise<{
  video_id: number
  position_ms: number
  chunk: ChunkMeta
  chunk_url: string
}> => movieRequest(`/videos/${videoId}/playback/seek`, undefined, { position_ms: positionMs })

export const fetchPlaybackState = (videoId: number): Promise<PlaybackState> =>
  movieRequest(`/videos/${videoId}/playback/state`)

export const savePlaybackState = (
  videoId: number,
  positionMs: number,
  completed = false,
): Promise<PlaybackState> =>
  movieRequest(`/videos/${videoId}/playback/state`, {
    method: 'PUT',
    body: JSON.stringify({ position_ms: positionMs, completed }),
  })

export const fetchNextVideo = (videoId: number): Promise<NextVideoResponse> =>
  movieRequest(`/videos/${videoId}/next`)

export const getVideoFileDurationMs = (file: File): Promise<number> =>
  new Promise((resolve, reject) => {
    const video = document.createElement('video')
    video.preload = 'metadata'
    video.onloadedmetadata = () => {
      const ms = Math.round(video.duration * 1000)
      URL.revokeObjectURL(video.src)
      if (!ms || ms <= 0) {
        reject(new Error('動画の長さを取得できませんでした'))
        return
      }
      resolve(ms)
    }
    video.onerror = () => {
      URL.revokeObjectURL(video.src)
      reject(new Error('動画ファイルの読み込みに失敗しました'))
    }
    video.src = URL.createObjectURL(file)
  })

/** ファイルを約 4MB ごとに分割してチャンクアップロード（単一チャンクも可） */
export const uploadVideoFile = async (
  videoId: number,
  file: File,
  durationMs: number,
  onProgress?: (uploaded: number, total: number) => void,
): Promise<void> => {
  const chunkSize = 4 * 1024 * 1024
  const totalChunks = Math.max(1, Math.ceil(file.size / chunkSize))
  const segmentDuration = Math.ceil(durationMs / totalChunks)

  for (let i = 0; i < totalChunks; i += 1) {
    const start = i * chunkSize
    const end = Math.min(start + chunkSize, file.size)
    const blob = file.slice(start, end)
    const startTimeMs = i * segmentDuration
    const endTimeMs = i === totalChunks - 1 ? durationMs : (i + 1) * segmentDuration
    await uploadChunk(videoId, i, startTimeMs, endTimeMs, blob)
    onProgress?.(i + 1, totalChunks)
  }

  await completeUpload(videoId, durationMs, totalChunks)
}

/** 全チャンクを結合して再生用 Blob URL を生成 */
export const buildVideoBlobUrl = async (
  videoId: number,
  mimeType: string,
  onProgress?: (loaded: number, total: number) => void,
): Promise<string> => {
  const { items } = await fetchChunkList(videoId)
  if (items.length === 0) {
    throw new Error('再生可能なチャンクがありません')
  }

  const buffers: ArrayBuffer[] = []
  for (let i = 0; i < items.length; i += 1) {
    const blob = await fetchChunkBlob(videoId, items[i].chunk_index)
    buffers.push(await blob.arrayBuffer())
    onProgress?.(i + 1, items.length)
  }

  const merged = new Blob(buffers, { type: mimeType })
  return URL.createObjectURL(merged)
}
