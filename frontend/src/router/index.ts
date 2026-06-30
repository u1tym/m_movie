import { createRouter, createWebHashHistory } from 'vue-router'
import VideoListView from '../views/VideoListView.vue'
import VideoRegisterView from '../views/VideoRegisterView.vue'
import VideoEditView from '../views/VideoEditView.vue'
import VideoPlayerView from '../views/VideoPlayerView.vue'
import GenreListView from '../views/GenreListView.vue'
import PlaylistListView from '../views/PlaylistListView.vue'
import PlaylistEditView from '../views/PlaylistEditView.vue'
import PlaylistPlayerView from '../views/PlaylistPlayerView.vue'

const router = createRouter({
  history: createWebHashHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', name: 'videos', component: VideoListView },
    { path: '/register', name: 'register', component: VideoRegisterView },
    { path: '/videos/:id', name: 'player', component: VideoPlayerView, props: true },
    { path: '/videos/:id/edit', name: 'edit', component: VideoEditView, props: true },
    { path: '/genres', name: 'genres', component: GenreListView },
    { path: '/playlists', name: 'playlists', component: PlaylistListView },
    { path: '/playlists/:id/edit', name: 'playlist-edit', component: PlaylistEditView, props: true },
    { path: '/playlists/:id/play', name: 'playlist-play', component: PlaylistPlayerView, props: true },
  ],
})

export default router
