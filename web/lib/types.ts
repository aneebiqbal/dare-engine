// Domain types the UI consumes. `api-types.ts` is generated from
// contracts/openapi.yaml by `make types`; keep the two in step when the
// contract changes.

export type Role = "admin" | "creator";

export type Me = {
  id: string;
  email: string | null;
  display_name: string | null;
  role: Role;
};

export type MissionCard = {
  id: string;
  question: string;
  hook_text: string;
  setup: string;
  win_condition: string;
  result_type: string;
  est_minutes: number;
  title_options: string[];
  mode: string;
  status: string;
  evidence: { askers: number; source_video_ids: string[] };
  policy: { spoiler: boolean; online_exploit: boolean };
};

export type Today = {
  date: string;
  daily: MissionCard | null;
  picks: MissionCard[];
  accepted: Record<string, string>;
};

export type PoolEntry = {
  id: string;
  card: MissionCard;
  score: number;
  state: "candidate" | "unverified" | "rejected";
};

export type List<T> = {
  items: T[];
  total: number;
  page: number;
  page_size: number;
};

export type Clip = {
  id: string;
  assignment_id: string | null;
  file_key: string | null;
  title: string | null;
  state: "queued" | "rendering" | "ready" | "approved" | "posted" | "discarded" | "failed";
  template: string | null;
  duration_seconds: number | null;
  stage: string | null;
  progress: number;
  error: string | null;
  layout: string | null;
  caption_style: string | null;
  voice_over: boolean;
  voice: string | null;
  export_title: string | null;
  export_description: string | null;
  export_tags: string[] | null;
  transcript: { start: number; end: number; text: string }[] | null;
  download_url: string | null;
};

export type Mark = {
  id: string;
  assignment_id: string;
  kind: string;
  stream_time: number;
  result: string | null;
};

export type Attempt = {
  rank: number;
  user_id: string;
  result_value: number | null;
  clip_id: string | null;
};

export type Stream = {
  id: string;
  rtmp_url: string;
  stream_key: string;
};

export type HistoryEntry = {
  mission_id: string;
  date: string;
  state: string;
  result_value: number | null;
  clip_id: string | null;
  clip_state: string | null;
  duration_seconds: number | null;
};

export type Results = {
  clips: {
    clip_id: string;
    title: string | null;
    views: number;
    avg_view_percentage: number | null;
    source: string;
  }[];
  by_type: { mode: string; clips: number; views: number }[];
};

export type Settings = {
  plan: "free" | "paid";
  clips_used: number;
  clips_limit: number;
  caption_style: string;
  layout_preference: string;
  voice_over_default: boolean;
  voice: string | null;
};

export type Suggestion = {
  suggestions: MissionCard[];
  fallback: boolean;
  notice?: string;
};

export type EditorResult = {
  hook_text: string;
  win_condition: string;
  title_spoiler?: boolean;
  fallback: boolean;
  notice?: string;
};

export type ReviewResult = {
  hook_line: string;
  score: number;
  weaknesses: string[];
  beats: { start: number; end: number }[];
  fallback: boolean;
  notice?: string;
};

export type ClipExport = {
  titles: string[];
  description: string;
  tags: string[];
  fallback: boolean;
  notice?: string;
};

export type HelpAnswer = {
  answer: string;
  fallback: boolean;
  notice?: string;
};

export type VoiceOver = {
  id: string;
  state: string;
  voice: string;
  text: string;
  audio_url: string | null;
};

export type TourProgress = {
  tour_id: string;
  step_index: number;
  completed: boolean;
  skipped: boolean;
};

export type User = {
  id: string;
  email: string | null;
  display_name: string | null;
  role: Role;
  created_at: string;
  last_login_at: string | null;
  locked: boolean;
};

export type Invite = {
  id: string;
  code: string;
  email: string | null;
  url?: string;
  created_at: string;
  expires_at: string;
  used: boolean;
  revoked: boolean;
};

export type Job = {
  id: string;
  kind: string;
  state: string;
  attempts: number;
  retry_count: number;
  error: string | null;
  payload: Record<string, unknown>;
  updated_at: string;
};

export type AuditEntry = {
  id: string;
  actor_id: string | null;
  action: string;
  target_type: string | null;
  target_id: string | null;
  meta: Record<string, unknown>;
  created_at: string;
};

export type AiUsage = {
  id: string;
  user_id: string | null;
  page: string;
  kind: string;
  provider: string;
  model: string;
  prompt_tokens: number;
  completion_tokens: number;
  latency_ms: number;
  fallback: boolean;
  created_at: string;
};

export type AiConfig = {
  provider: string;
  base_url: string;
  model: string;
  key_present: boolean;
  configured: boolean;
};
