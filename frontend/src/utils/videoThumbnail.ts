/** 動画ファイルの指定秒数付近のフレームを JPEG Blob として切り出す */
export const captureVideoFrame = (file: File, timeSec: number): Promise<Blob> =>
  new Promise((resolve, reject) => {
    const video = document.createElement('video')
    video.preload = 'auto'
    video.muted = true
    video.playsInline = true
    const url = URL.createObjectURL(file)

    const cleanup = (): void => {
      URL.revokeObjectURL(url)
      video.removeAttribute('src')
      video.load()
    }

    const capture = (): void => {
      if (video.videoWidth === 0 || video.videoHeight === 0) {
        cleanup()
        reject(new Error('動画フレームを取得できませんでした'))
        return
      }

      const canvas = document.createElement('canvas')
      canvas.width = video.videoWidth
      canvas.height = video.videoHeight
      const ctx = canvas.getContext('2d')
      if (!ctx) {
        cleanup()
        reject(new Error('サムネイルの生成に失敗しました'))
        return
      }

      ctx.drawImage(video, 0, 0, canvas.width, canvas.height)
      canvas.toBlob(
        (blob) => {
          cleanup()
          if (blob) {
            resolve(blob)
          } else {
            reject(new Error('サムネイルの生成に失敗しました'))
          }
        },
        'image/jpeg',
        0.85,
      )
    }

    const onError = (): void => {
      cleanup()
      reject(new Error('動画ファイルの読み込みに失敗しました'))
    }

    video.onerror = onError

    video.onloadeddata = () => {
      const maxSec = Math.max(0, video.duration - 0.001)
      const target = Math.min(Math.max(0, timeSec), maxSec)

      if (target <= 0.001) {
        capture()
        return
      }

      const onSeeked = (): void => {
        video.removeEventListener('seeked', onSeeked)
        capture()
      }
      video.addEventListener('seeked', onSeeked)
      video.currentTime = target
    }

    video.src = url
    video.load()
  })

/**
 * サムネイル未指定時のデフォルト画像を生成する。
 * - 5秒超: 5秒地点のフレーム
 * - 5秒以内: 先頭フレーム
 */
export const generateDefaultThumbnail = (file: File, durationMs: number): Promise<Blob> => {
  const timeSec = durationMs > 5000 ? 5 : 0
  return captureVideoFrame(file, timeSec)
}
