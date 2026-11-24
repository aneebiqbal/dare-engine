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
  assignments?: { id: string; mission_id: string; state: string }[];
};

export type MissionSource = {
  kind: "youtube" | "reddit" | "news" | string;
  title: string;
  url: string;
  external_id: string | null;
  published_at: string | null;
};

export type PoolEntry = {
  id: string;
  card: MissionCard;
  score: number;
  state: "candidate" | "unverified" | "rejected";
  sources?: MissionSource[];
};

export type Game = {
  id: string;
  slug: string;
  name: string;
  external_id: string | null;
  source: string;
  genre: string | null;
  release_date: string | null;
  art_url: string | null;
  enabled: boolean;
  created_at: string;
  candidates?: number;
  approved?: number;
  gamers?: number;
  last_run?: {
    id: string;
    status: string;
    stage: string | null;
    detail: string | null;
    ideas_count: number;
    fallback: boolean;
    source_fallback?: boolean;
    ai_fallback?: boolean;
    created_at: string;
  } | null;
};

export type GameSearchEntry = {
  slug: string;
  name: string;
  external_id: string | null;
  genre: string | null;
  release_date: string | null;
  art_url: string | null;
};

export type ResearchRun = {
  id: string;
  game_id: string;
  game_name: string;
  status: string;
  stage: string | null;
  detail: string | null;
  source_counts: Record<string, number>;
  ideas_count: number;
  fallback: boolean;
  source_fallback: boolean;
  ai_fallback: boolean;
  error: string | null;
  created_at: string;
  finished_at: string | null;
};

export type GameProfile = {
  game: Game;
  candidates: PoolEntry[];
  approved: PoolEntry[];
  assigned: {
    assignment_id: string;
    user_id: string;
    display_name: string;
    state: string;
    date: string;
    mission_id: string;
  }[];
  runs: ResearchRun[];
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
  commentary?: string | null;
  platform?: string;
  download_url: string | null;
  thumb_url?: string | null;
};

export type SsdVideo = {
  name: string;
  path: string;
  size_bytes: number;
  duration_seconds?: number;
  width?: number;
  height?: number;
  error?: string;
};

export type SsdDrive = {
  name: string;
  path: string;
  error?: string;
  videos: SsdVideo[];
};

export type SsdResponse = {
  enabled: boolean;
  reason?: string;
  error?: string;
  how_to?: string;
  mount?: string;
  drives: SsdDrive[];
};

export type ObsStatus = {
  enabled: boolean;
  connected: boolean;
  error?: string;
  detail?: string;
  how_to_enable?: string;
  obs_version?: string;
  websocket_version?: string;
  rpc_version?: number;
  streaming?: boolean;
  recording?: boolean;
  record_paused?: boolean;
  scene?: string;
  audio_inputs?: { name: string; muted: boolean }[];
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
  question?: string | null;
};

export type Results = {
  clips: {
    clip_id: string;
    title: string | null;
    views: number;
    avg_view_percentage: number | null;
    swiped: number;
    saves: number;
    shares: number;
    source: string;
  }[];
  by_type: {
    mode: string;
    clips: number;
    views: number;
    avg_view_percentage?: number | null;
    swiped: number;
    saves: number;
    shares: number;
  }[];
  leading: {
    views: number;
    swiped: number;
    swipe_through_rate: number | null;
    saves: number;
    shares: number;
    saves_per_1000: number | null;
    shares_per_1000: number | null;
  };
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
  stage?: string | null;
};

export type AuditEntry = {
  id: string;
  actor_id: string | null;
  action: string;
  target_type: string | null;
  target_id: string | null;
  meta: Record<string, unknown>;
  created_at: string;
  actor_name?: string | null;
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

export type IntegrationKey = {
  name: string;
  label: string;
  group: string;
  docs: string;
  env_var: string;
  masked: string;
  configured: boolean;
  source: "stored" | "env" | "none";
  status: "connected" | "invalid" | "unreachable" | "untested";
  status_detail: string | null;
  tested_at: string | null;
};

export type KeyStatusResponse = {
  integrations: IntegrationKey[];
  research_sources_configured: boolean;
};

export type KeyTestResponse = {
  ok: boolean;
  status: IntegrationKey["status"];
  detail: string;
};

export type StudioCandidate = {
  id: string;
  start: number;
  end: number;
  score: number;
  reasons: string[];
  state: string;
  template_id: string | null;
  clip_id: string | null;
  /** audio = the cheap detector; vision = the sampled VLM pass. */
  source?: "audio" | "vision";
  thumb_url?: string | null;
};

export type StudioRecording = {
  recording: {
    id: string;
    filename: string;
    duration_seconds: number;
    width: number;
    height: number;
  };
  compute: {
    whisper_device: string | null;
    whisper_compute_type: string | null;
    encoder: string | null;
    gpu: boolean;
  };
  vision: {
    model: string | null;
    seconds_added: number | null;
  };
  job: { kind: string; state: string; stage: string | null } | null;
  candidates: StudioCandidate[];
};

export type EngineEvent = {
  id: string;
  kind: string;
  detail: string | null;
  created_at: string | null;
};

export type WizardStep = {
  id: string;
  title: string;
  body: string;
  help: string;
  status: "pending" | "done" | "failed";
  detail: string | null;
  updated_at: string | null;
};

export type WizardState = {
  steps: WizardStep[];
  ready: boolean;
  next: string | null;
};

export type Platform = {
  id: string;
  label: string;
  aspect: string;
  width: number;
  height: number;
  min_seconds: number;
  max_seconds: number;
  hook_seconds: number;
  caption_style: string;
  hint: string;
};

export type Project = {
  id: string;
  name: string;
  game_id: string | null;
  recording_id: string | null;
  stream_id: string | null;
  vision: boolean;
  platform?: string;
  stage: "planned" | "recording" | "imported" | "analyzing" | "clips_ready" | "reviewed" | "exported";
  stage_index: number;
  progress: number;
  stage_note: string | null;
  candidates: number;
  clips: { ready: number; total: number; reviewed: number };
  pipeline?: PipelineRun | null;
  queued: boolean;
  queue_position: number | null;
  created_at: string | null;
  updated_at: string | null;
};

export type PipelineRun = {
  id: string;
  project_id?: string;
  state: "queued" | "running" | "paused" | "done" | "failed";
  stage: string;
  progress: number;
  action: string;
  eta_seconds: number | null;
  remaining_seconds: number | null;
  model_loaded: string;
  platform?: string;
  stage_timings: Record<string, number>;
  compute_path: string;
  error: string | null;
  no_speech: boolean;
  name?: string;
  created_at?: string | null;
  finished_at?: string | null;
};

export type PipelineCandidate = {
  id: string;
  start: number;
  end: number;
  cheap_score: number;
  vision_score: number | null;
  final_score: number;
  reasons: string[];
  vision_reason: string | null;
  origin: "ai" | "user";
  selected: boolean;
  status: string;
  label?: string | null;
  hook?: string | null;
  reason?: string | null;
  scores?: Record<string, number> | null;
  composite?: number | null;
  thumb_url: string | null;
  clip_id: string | null;
  error: string | null;
};

export type PipelineClip = {
  id: string;
  state: string;
  duration_seconds: number | null;
  title: string | null;
  layout: string | null;
  caption_style: string | null;
  platform?: string;
  thumb_url: string;
  download_url: string;
};

export type ErrorReport = {
  id: string;
  message: string;
  path: string | null;
  created_at: string;
  user: string | null;
};

export type SystemLoad = {
  cpu_percent: number;
  memory_percent: number;
  gpu: {
    utilization_percent: number;
    memory_used_mb: number;
    memory_total_mb: number;
  } | null;
};

export type OllamaModel = {
  name: string;
  size_bytes: number;
  modified_at: string | null;
};

export type RunningModel = {
  name: string;
  size_bytes: number;
  size_vram_bytes: number;
  expires_at: string | null;
};

export type HostMemory = {
  total_bytes: number;
  used_bytes: number;
  percent: number;
};

export type MlxState = {
  model: string;
  transcribing: boolean;
  last_elapsed_s: number | null;
  peak_memory_bytes: number | null;
  downloaded: boolean;
  error: string | null;
};

export type ModelProvider = {
  llm_provider: string;
  llm_model: string;
  llm_base_url: string;
  configured: boolean;
  asr: string;
  mlx_model: string;
  vision_model: string;
};

export type ModelStatus = {
  bridge: "up" | "down";
  error: string | null;
  provider: ModelProvider;
  engine: {
    compute: string;
    model: string;
    ollama: {
      available: boolean;
      error: string | null;
      models: OllamaModel[];
      running: RunningModel[];
    };
    mlx: MlxState;
    host: HostMemory;
  } | null;
};

export type PullTask = {
  id: string;
  name: string;
  done: boolean;
  progress: number;
  status: string;
  error: string | null;
};

export type CalendarEntry = {
  id: string;
  clip_id: string;
  date: string;
  platform: string;
  state: string;
  title: string;
  duration_seconds: number | null;
};

export type CalendarResponse = {
  month: string;
  entries: CalendarEntry[];
  unscheduled: { id: string; title: string; duration_seconds: number | null }[];
  warnings: string[];
  daily_limit: number;
  platforms: Record<string, string>;
  gated: string[];
};

export type AdminClip = {
  id: string;
  title: string | null;
  state: string;
  duration_seconds: number | null;
  created_at: string;
};

export type LongForm = {
  id: string;
  title: string;
  state: string;
  clip_ids: string[];
  error?: string | null;
  created_at: string;
  intro?: string | null;
  outro?: string | null;
  download_url?: string | null;
};

export type ProviderStatus = {
  env: {
    llm_provider: string;
    llm_model: string;
    llm_base_url: string;
    configured: boolean;
  };
  stored: Record<string, string | null>;
  effective: {
    llm_provider: string;
    llm_model: string;
    llm_base_url: string;
    asr: string;
    configured: boolean;
  };
};

export type ResultClip = {
  clip_id: string;
  title: string | null;
  views: number;
  avg_view_percentage: number | null;
  swiped: number;
  saves: number;
};

export type AdminOverview = {
  generated_at: string;
  jobs: {
    counts: Record<string, number>;
    active: Job[];
    running: number;
    failed: number;
  };
  research: { active: ResearchRun[]; recent: ResearchRun[] };
  projects: Project[];
  pool: { candidate: number; unverified: number; rejected: number };
  keys: {
    research_sources_configured: boolean;
    failing: string[];
    unreachable: string[];
    integrations: IntegrationKey[];
  };
  system: SystemLoad | null;
  activity: EngineEvent[];
  results: { best: ResultClip | null; worst: ResultClip | null; total_views: number };
  clips_today: number;
  users: { total: number; admins: number; locked: number };
  invites: { open: number };
};
