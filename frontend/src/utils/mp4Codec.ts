export type Mp4VideoCodec = 'avc' | 'hevc' | 'unknown'

const CODEC_LABELS: Record<Mp4VideoCodec, string> = {
  avc: 'H.264 (AVC)',
  hevc: 'H.265 (HEVC)',
  unknown: '不明',
}

export const mp4VideoCodecLabel = (codec: Mp4VideoCodec): string => CODEC_LABELS[codec]

/** MP4 先頭付近から映像コーデック（avc1 / hvc1 等）を検出する */
export const detectMp4VideoCodec = async (file: File): Promise<Mp4VideoCodec> => {
  const sampleSize = Math.min(file.size, 512 * 1024)
  const buffer = await file.slice(0, sampleSize).arrayBuffer()
  const bytes = new Uint8Array(buffer)
  const text = new TextDecoder('latin1').decode(bytes)

  if (text.includes('hvc1') || text.includes('hev1') || text.includes('hvcC') || text.includes('hevC')) {
    return 'hevc'
  }
  if (text.includes('avc1') || text.includes('avc3') || text.includes('avcC')) {
    return 'avc'
  }
  return 'unknown'
}

export const isIphoneWebCompatibleCodec = (codec: Mp4VideoCodec): boolean =>
  codec === 'avc' || codec === 'unknown'

export const hevcUploadWarning =
  'H.265 (HEVC / libx265) の動画は iPhone のブラウザでは再生できません。H.264 (libx264) でエンコードし直してください。'

export const hevcPlaybackError =
  'H.265 (HEVC) の動画は iPhone のブラウザでは再生できません。H.264 (libx264) で再エンコードした MP4 を登録してください。'

export const ffmpegH264Command = (inputPath = 'input.mp4', outputPath = 'output.mp4'): string =>
  `ffmpeg -i ${inputPath} -c:v libx264 -profile:v main -level 4.0 -pix_fmt yuv420p -c:a aac -movflags +faststart ${outputPath}`
