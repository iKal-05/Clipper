const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Request failed' }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export const api = {
  health: () => request<{ status: string }>('/api/health'),
  createJob: (url: string, prefs?: Partial<JobCreate>) =>
    request<Job>('/api/jobs', { method: 'POST', body: JSON.stringify({ url, ...prefs }) }),
  getJob: (id: string) => request<Job>(`/api/jobs/${id}`),
  listClips: (jobId: string) => request<Clip[]>(`/api/jobs/${jobId}/clips`),
  selectClips: (jobId: string, clipIds: string[], trims?: TrimSpan[]) =>
    request<{ job_id: string }>(`/api/jobs/${jobId}/clips/select`, {
      method: 'POST',
      body: JSON.stringify({ clip_ids: clipIds, trims }),
    }),
  listAssets: (jobId: string) => request<Asset[]>(`/api/jobs/${jobId}/assets`),
  getClipVideo: (clipId: string) => `${API_BASE}/api/clips/${clipId}/video`,
  getClipThumbnail: (clipId: string) => `${API_BASE}/api/clips/${clipId}/thumbnail`,
  streamLog: (jobId: string) => `${API_BASE}/api/jobs/${jobId}/log`,
  deleteJob: (id: string) => request<void>(`/api/jobs/${id}`, { method: 'DELETE' }),
};

export interface JobCreate {
  url: string;
  max_clip_seconds?: number;
  max_clips?: number;
  moment_filters?: string[];
  min_score?: number;
  whisper_model?: string;
  use_cloud_model?: boolean;
}

export interface JobPrefs {
  max_clip_seconds: number;
  max_clips: number;
  moment_filters?: string[];
  min_score?: number;
  whisper_model: string;
  use_cloud_model: boolean;
}

export interface Job {
  id: string;
  url: string;
  status: JobStatus;
  current_stage?: string;
  pct: number;
  prefs: JobPrefs;
  error?: string;
  created_at: number;
  updated_at: number;
  clips: string[];
  assets: Record<string, Asset>;
}

export type JobStatus =
  | 'queued'
  | 'downloading'
  | 'transcribing'
  | 'analyzing'
  | 'scoring'
  | 'cutting'
  | 'reframing'
  | 'rendering'
  | 'subtitle'
  | 'assets'
  | 'done'
  | 'error';

export interface Clip {
  id: string;
  job_id: string;
  start: number;
  end: number;
  duration: number;
  moment_labels: string[];
  score: number;
  thumbnail_path?: string;
  video_path?: string;
}

export interface SelectClips {
  clip_ids: string[];
  trims?: TrimSpan[];
}

export interface TrimSpan {
  clip_id: string;
  start: number;
  end: number;
}

export interface Asset {
  clip_id: string;
  title: string;
  hook: string;
  description: string;
  hashtags: string[];
  platform_tags: string[];
  thumbnail_path?: string;
  keywords: string[];
}

export interface Moment {
  label: string;
  start: number;
  end: number;
  score: number;
  evidence: Record<string, unknown>;
}

export type ProgressEvent =
  | { type: 'stage'; stage: string; status: 'started' | 'finished'; pct: number }
  | { type: 'log'; level: 'info' | 'warn' | 'error'; msg: string }
  | { type: 'clips_ready'; count: number }
  | { type: 'done' }
  | { type: 'error'; message: string };