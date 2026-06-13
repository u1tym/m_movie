import { createRouter, createWebHashHistory } from 'vue-router'
import VideoListView from '../views/VideoListView.vue'
import VideoRegisterView from '../views/VideoRegisterView.vue'
import VideoEditView from '../views/VideoEditView.vue'
import VideoPlayerView from '../views/VideoPlayerView.vue'
import GenreListView from '../views/GenreListView.vue'

const router = createRouter({
  history: createWebHashHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', name: 'videos', component: VideoListView },
    { path: '/register', name: 'register', component: VideoRegisterView },
    { path: '/videos/:id', name: 'player', component: VideoPlayerView, props: true },
    { path: '/videos/:id/edit', name: 'edit', component: VideoEditView, props: true },
    { path: '/genres', name: 'genres', component: GenreListView },
  ],
})

export default router
