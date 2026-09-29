export interface VideoItem {
  uid: string;
  platform: string;
  url: string;
  native_id?: string;
  title?: string;
  author?: string;
  author_id?: string;
  views?: number;
  likes?: number;
  comments?: number;
  shares?: number;
  collects?: number;
  duration?: number;
  score?: number;
  state: 'discovered' | 'queued' | 'downloading' | 'downloaded' | 'qc_passed' | 'qc_failed' | 'duplicate' | 'exported' | 'dubbed' | 'published' | 'rejected' | 'error';
  attempts?: number;
  last_error?: string;
  updated_at?: number;
  topic?: string;
  source?: string;
}

export interface RunItem {
  id: number;
  stage: string;
  topic?: string;
  started?: number;
  finished?: number;
  ok?: number;
  failed?: number;
  note?: string;
}

export interface SceneItem {
  scene_id: string;
  chapter_id?: string;
  narration: string;
  estimated_duration_sec: number;
  visual_intent?: string;
  source_ids?: string[];
  asset_ids?: string[];
  trim_in?: number;
  trim_out?: number;
  framing?: string;
  on_screen_text?: string;
  text_effect?: string;
  playback_rate?: number;
  review_notes?: string;
  match_method?: string;
  match_reason?: string;
  status?: string;
  format?: string;
  frame_rate?: number;
  tts_profile?: string;
  voice_resolution?: {
    preset?: string;
    tts_backend?: string;
    speed?: number;
    pitch?: number;
  };
  media?: string;
  audio?: string;
}

export interface ProjectBrief {
  title: string;
  aspect_ratio: '9:16' | '16:9' | '1:1';
}

export interface ProjectSummary {
  id: string;
  title: string;
  aspectRatio: string;
  scenesCount: number;
  duration: number;
  updatedAt: number;
}

export interface ProjectDetail {
  id: string;
  brief: ProjectBrief;
  scenes: SceneItem[];
  previewProfile: any;
  subtitles: string;
  script?: string;
  roadmap?: string;
  mediaFiles: string[];
  audioFiles: string[];
}

export interface SubtitleCue {
  id: number;
  start: number; // in seconds
  end: number;   // in seconds
  startStr: string;
  endStr: string;
  text: string;
}

export type AssetSourceType = 'reddit' | 'youtube' | 'tiktok' | 'news' | 'twitter' | 'facebook';

export interface ResearchAsset {
  id: string;
  title: string;
  source: AssetSourceType;
  author: string;
  url: string;
  previewUrl: string;
  aspectRatio?: '9:16' | '16:9' | '1:1';
  summary?: string;
  score: number;
  views: number;
  likes: number;
  comments: number;
  shares?: number;
  tags: string[];
  branch: 'entertainment' | 'art' | 'sports' | 'news' | 'custom';
  createdAgo: string;
}

export interface AgentJob {
  id: string;
  scene_id?: string;
  prompt: string;
  model: string;
  status: 'queued' | 'processing' | 'ready' | 'failed' | 'kept' | 'discarded';
  progress: number;
  previewUrl: string;
  createdAt: number;
  duration?: number;
  error?: string;
}

export type SpeedCurveType = 'constant' | 'hero' | 'montage' | 'bullet_time' | 'custom';

export interface TimelineClip {
  id: string;
  trackId: 'main' | 'broll' | 'audio' | 'captions';
  start: number; // seconds
  duration: number; // seconds
  title: string;
  mediaUrl?: string;
  speedCurve?: SpeedCurveType;
  speedRate?: number;
  trimIn?: number;
  trimOut?: number;
  color?: string;
}

export interface BatchVideoVariant {
  id: string;
  title: string;
  hookType: 'shock' | 'question' | 'negative' | 'story' | 'statistic';
  hookText: string;
  visualStyle: 'cyberpunk' | 'cinematic' | 'anime' | 'vintage' | 'photorealistic';
  voicePreset: string;
  captionsStyle: 'hormozi' | 'gold_glow' | 'minimal_orange' | 'karaoke';
  aspectRatio: '9:16' | '16:9';
  status: 'queued' | 'rendering' | 'ready' | 'failed';
  progress: number;
  duration: number;
  thumbnailUrl: string;
  videoUrl?: string;
  targetPlatforms: ('tiktok' | 'youtube' | 'reels' | 'facebook')[];
}
