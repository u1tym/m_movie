import type {
  LastPlayback,
  PlaylistDetail,
  PlaylistPlaybackItem,
  PlaylistSummary,
} from '../types/playlist'
import type { Paginated } from '../types/movie'
import { movieRequest } from './client'

export const fetchPlaylists = (
  page = 1,
  perPage = 20,
): Promise<Paginated<PlaylistSummary>> =>
  movieRequest('/playlists', undefined, { page, per_page: perPage })

export const createPlaylist = (body: {
  name: string
  description?: string | null
}): Promise<PlaylistDetail> =>
  movieRequest('/playlists', { method: 'POST', body: JSON.stringify(body) })

export const fetchPlaylist = (playlistId: number): Promise<PlaylistDetail> =>
  movieRequest(`/playlists/${playlistId}`)

export const updatePlaylist = (
  playlistId: number,
  body: { name?: string; description?: string | null },
): Promise<PlaylistDetail> =>
  movieRequest(`/playlists/${playlistId}`, { method: 'PUT', body: JSON.stringify(body) })

export const deletePlaylist = (playlistId: number): Promise<void> =>
  movieRequest(`/playlists/${playlistId}`, { method: 'DELETE' })

export const updatePlaylistItems = (
  playlistId: number,
  videoIds: number[],
): Promise<PlaylistDetail> =>
  movieRequest(`/playlists/${playlistId}/items`, {
    method: 'PUT',
    body: JSON.stringify({ items: videoIds.map((video_id) => ({ video_id })) }),
  })

export const startPlaylistPlayback = (
  playlistId: number,
  resume = true,
): Promise<PlaylistPlaybackItem> =>
  movieRequest(`/playlists/${playlistId}/playback/start`, {
    method: 'POST',
    body: JSON.stringify({ resume }),
  })

export const fetchNextPlaylistItem = (
  playlistId: number,
  playlistItemId: number,
): Promise<{ has_next: boolean; item: PlaylistPlaybackItem | null }> =>
  movieRequest(`/playlists/${playlistId}/items/${playlistItemId}/next`)

export const savePlaylistPlaybackState = (
  playlistId: number,
  playlistItemId: number,
  positionMs: number,
): Promise<void> =>
  movieRequest(
    `/playlists/${playlistId}/items/${playlistItemId}/playback/state?position_ms=${positionMs}`,
    { method: 'PUT' },
  )

export const fetchLastPlayback = (): Promise<LastPlayback> =>
  movieRequest('/playback/last')
