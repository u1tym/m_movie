import { fetchChunkBlob } from '../api/movie'
import type { ChunkMeta } from '../types/movie'

const MP4_CODEC_FALLBACKS = [
  'video/mp4; codecs="avc1.640028, mp4a.40.2"',
  'video/mp4; codecs="avc1.42E01E, mp4a.40.2"',
  'video/mp4; codecs="avc1.4D401E, mp4a.40.2"',
]

const fourCC = (view: DataView, offset: number): string =>
  String.fromCharCode(
    view.getUint8(offset),
    view.getUint8(offset + 1),
    view.getUint8(offset + 2),
    view.getUint8(offset + 3),
  )

const parseBoxHeader = (
  view: DataView,
  offset: number,
  limit: number,
): { size: number; type: string; headerSize: number; bodyStart: number } | null => {
  if (offset + 8 > limit) return null
  let size = view.getUint32(offset)
  const type = fourCC(view, offset + 4)
  let headerSize = 8
  if (size === 1) {
    if (offset + 16 > limit) return null
    size = Number(view.getBigUint64(offset + 8))
    headerSize = 16
  } else if (size === 0) {
    size = limit - offset
  }
  if (size < headerSize) return null
  return { size, type, headerSize, bodyStart: offset + headerSize }
}

/** 先頭チャンクから MSE 用 codecs 文字列を抽出する */
export const extractMp4Codecs = (buffer: ArrayBuffer): string | null => {
  const view = new DataView(buffer)
  const limit = buffer.byteLength
  const codecs: string[] = []

  const walk = (start: number, end: number, inStsd: boolean): void => {
    let offset = start
    while (offset + 8 <= end) {
      const header = parseBoxHeader(view, offset, end)
      if (!header) break
      const boxEnd = Math.min(offset + header.size, end)

      if (header.type === 'stsd') {
        walk(header.bodyStart + 8, boxEnd, true)
        offset = boxEnd
        continue
      }

      if (
        inStsd &&
        (header.type === 'avc1' ||
          header.type === 'avc3' ||
          header.type === 'hvc1' ||
          header.type === 'hev1')
      ) {
        if (header.bodyStart + 7 <= boxEnd) {
          const p = view.getUint8(header.bodyStart + 5).toString(16).padStart(2, '0').toUpperCase()
          const c = view.getUint8(header.bodyStart + 6).toString(16).padStart(2, '0').toUpperCase()
          const l = view.getUint8(header.bodyStart + 7).toString(16).padStart(2, '0').toUpperCase()
          codecs.push(`${header.type}.${p}${c}${l}`)
        }
      }

      if (inStsd && header.type === 'mp4a') {
        codecs.push('mp4a.40.2')
      }

      if (['moov', 'trak', 'mdia', 'minf', 'stbl'].includes(header.type)) {
        walk(header.bodyStart, boxEnd, false)
      }

      offset = boxEnd
    }
  }

  walk(0, limit, false)
  if (codecs.length === 0) return null
  return codecs.join(', ')
}

export const resolveMseMimeType = (firstChunk: ArrayBuffer, mimeType: string): string => {
  const detected = extractMp4Codecs(firstChunk)
  if (detected) {
    const mime = `video/mp4; codecs="${detected}"`
    if (MediaSource.isTypeSupported(mime)) return mime
  }

  for (const candidate of MP4_CODEC_FALLBACKS) {
    if (MediaSource.isTypeSupported(candidate)) return candidate
  }

  return mimeType.startsWith('video/') ? MP4_CODEC_FALLBACKS[0] : mimeType
}

const isTimeBuffered = (video: HTMLVideoElement, timeSec: number): boolean => {
  const ranges = video.buffered
  for (let i = 0; i < ranges.length; i += 1) {
    if (ranges.start(i) <= timeSec && timeSec <= ranges.end(i)) return true
  }
  return false
}

const waitSourceBuffer = (sourceBuffer: SourceBuffer): Promise<void> =>
  new Promise((resolve, reject) => {
    if (!sourceBuffer.updating) {
      resolve()
      return
    }
    const onUpdateEnd = (): void => {
      sourceBuffer.removeEventListener('updateend', onUpdateEnd)
      sourceBuffer.removeEventListener('error', onError)
      resolve()
    }
    const onError = (): void => {
      sourceBuffer.removeEventListener('updateend', onUpdateEnd)
      sourceBuffer.removeEventListener('error', onError)
      reject(new Error('SourceBuffer の更新に失敗しました'))
    }
    sourceBuffer.addEventListener('updateend', onUpdateEnd)
    sourceBuffer.addEventListener('error', onError)
  })

const appendToSourceBuffer = async (
  sourceBuffer: SourceBuffer,
  data: ArrayBuffer,
): Promise<void> => {
  await waitSourceBuffer(sourceBuffer)
  await new Promise<void>((resolve, reject) => {
    const onUpdateEnd = (): void => {
      sourceBuffer.removeEventListener('updateend', onUpdateEnd)
      sourceBuffer.removeEventListener('error', onError)
      resolve()
    }
    const onError = (): void => {
      sourceBuffer.removeEventListener('updateend', onUpdateEnd)
      sourceBuffer.removeEventListener('error', onError)
      reject(new Error('チャンクの追加に失敗しました'))
    }
    sourceBuffer.addEventListener('updateend', onUpdateEnd)
    sourceBuffer.addEventListener('error', onError)
    try {
      sourceBuffer.appendBuffer(data)
    } catch (e) {
      sourceBuffer.removeEventListener('updateend', onUpdateEnd)
      sourceBuffer.removeEventListener('error', onError)
      reject(e instanceof Error ? e : new Error('チャンクの追加に失敗しました'))
    }
  })
}

export interface MseLoaderOptions {
  video: HTMLVideoElement
  videoId: number
  items: ChunkMeta[]
  mimeType: string
  startPositionMs: number
  onProgress?: (loaded: number, total: number) => void
  signal?: AbortSignal
}

export interface MseLoaderHandle {
  /** 再生開始位置までバッファが溜まったら resolve */
  waitUntilReady: Promise<void>
  /** 全チャンクの append が完了したら resolve */
  waitUntilComplete: Promise<void>
  destroy: () => void
}

export const isMseSupported = (): boolean =>
  typeof MediaSource !== 'undefined' && MediaSource.isTypeSupported(MP4_CODEC_FALLBACKS[0])

const canStartPlayback = (
  video: HTMLVideoElement,
  startPositionMs: number,
  appendedAll: boolean,
): boolean => {
  if (appendedAll) return true
  if (video.readyState < HTMLMediaElement.HAVE_METADATA) return false
  const targetSec = startPositionMs / 1000
  return targetSec === 0 || isTimeBuffered(video, targetSec)
}

/** チャンクを順次 SourceBuffer に追加して MSE 再生する */
export const startMseLoader = (options: MseLoaderOptions): MseLoaderHandle => {
  const { video, videoId, items, mimeType, startPositionMs, onProgress, signal } = options
  const mediaSource = new MediaSource()
  const objectUrl = URL.createObjectURL(mediaSource)
  let sourceBuffer: SourceBuffer | null = null
  let destroyed = false
  let readyResolved = false
  let readyResolve!: () => void
  let readyReject!: (reason?: unknown) => void

  const waitUntilReady = new Promise<void>((resolve, reject) => {
    readyResolve = resolve
    readyReject = reject
  })

  video.src = objectUrl

  const destroy = (): void => {
    destroyed = true
    if (mediaSource.readyState === 'open') {
      try {
        mediaSource.endOfStream()
      } catch {
        // ignore
      }
    }
    URL.revokeObjectURL(objectUrl)
    video.removeAttribute('src')
    video.load()
  }

  const throwIfAborted = (): void => {
    if (destroyed || signal?.aborted) {
      throw new Error('読み込みが中断されました')
    }
  }

  const markReady = (): void => {
    if (readyResolved) return
    readyResolved = true
    if (startPositionMs > 0) {
      video.currentTime = startPositionMs / 1000
    }
    readyResolve()
  }

  const waitUntilComplete = (async () => {
    await new Promise<void>((resolve, reject) => {
      if (mediaSource.readyState === 'open') {
        resolve()
        return
      }
      const onOpen = (): void => {
        mediaSource.removeEventListener('sourceopen', onOpen)
        mediaSource.removeEventListener('error', onError)
        resolve()
      }
      const onError = (): void => {
        mediaSource.removeEventListener('sourceopen', onOpen)
        mediaSource.removeEventListener('error', onError)
        reject(new Error('MediaSource の初期化に失敗しました'))
      }
      mediaSource.addEventListener('sourceopen', onOpen)
      mediaSource.addEventListener('error', onError)
    })

    throwIfAborted()

    const sorted = [...items].sort((a, b) => a.chunk_index - b.chunk_index)
    if (sorted.length === 0) {
      throw new Error('再生可能なチャンクがありません')
    }

    const firstBuffer = await (await fetchChunkBlob(videoId, sorted[0].chunk_index)).arrayBuffer()
    throwIfAborted()

    const mseMime = resolveMseMimeType(firstBuffer, mimeType)
    sourceBuffer = mediaSource.addSourceBuffer(mseMime)
    sourceBuffer.mode = 'segments'

    for (let i = 0; i < sorted.length; i += 1) {
      throwIfAborted()
      const buffer =
        i === 0 ? firstBuffer : await (await fetchChunkBlob(videoId, sorted[i].chunk_index)).arrayBuffer()
      throwIfAborted()

      if (!sourceBuffer) throw new Error('SourceBuffer が初期化されていません')
      await appendToSourceBuffer(sourceBuffer, buffer)
      onProgress?.(i + 1, sorted.length)

      if (canStartPlayback(video, startPositionMs, i === sorted.length - 1)) {
        markReady()
      }
    }

    if (mediaSource.readyState === 'open') {
      mediaSource.endOfStream()
    }
    if (!readyResolved) {
      markReady()
    }
  })().catch((e) => {
    readyReject(e)
    throw e
  })

  return { waitUntilReady, waitUntilComplete, destroy }
}
