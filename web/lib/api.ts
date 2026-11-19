import type {
  AiConfig,
  AiUsage,
  Attempt,
  AuditEntry,
  Clip,
  ClipExport,
  EditorResult,
  Game,
  GameProfile,
  GameSearchEntry,
  HelpAnswer,
  HistoryEntry,
  Invite,
  Job,
  List,
  Mark,
  Me,
  ObsStatus,
  SsdDrive,
  SsdResponse,
  SsdVideo,
  MissionCard,
  PoolEntry,
  ResearchRun,
  Results,
  ReviewResult,
  Settings,
  Stream,
  StudioCandidate,
  StudioRecording,
  Suggestion,
  SystemLoad,
  ModelStatus,
  PullTask,
  Today,
  TourProgress,
  User,
  VoiceOver,
} from "./types";

export type {
  AiConfig,
  AiUsage,
  Attempt,
  AuditEntry,
  Clip,
  ClipExport,
  EditorResult,
  Game,
  GameProfile,
  GameSearchEntry,
  HelpAnswer,
  HistoryEntry,
  Invite,
  Job,
  List,
  Mark,
  Me,
  ObsStatus,
  SsdDrive,
  SsdResponse,
  SsdVideo,
  MissionCard,
  PoolEntry,
  ResearchRun,
  Results,
  ReviewResult,
  Settings,
  Stream,
  StudioCandidate,
  StudioRecording,
  Suggestion,
  SystemLoad,
  ModelStatus,
  PullTask,
  Today,
  TourProgress,
  User,
  VoiceOver,
} from "./types";

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

const SERVER_BASE = process.env.API_URL ?? "http://api:8000";
export const MOCK = process.env.NEXT_PUBLIC_API_MOCK === "1";

// Slow, stable endpoints cached in the browser. Never cache anything polled for
// freshness (studio candidates, clip render state).
const CLIENT_CACHE: [RegExp, number][] = [
  [/^\/admin\/setup$/, 60_000],
  [/^\/help\/guide$/, 60_000],
  [/^\/tours$/, 30_000],
  [/^\/me$/, 30_000],
];
const clientCache = new Map<string, { at: number; value: unknown }>();

function cacheTtl(path: string): number | undefined {
  return typeof window === "undefined"
    ? undefined
    : CLIENT_CACHE.find(([re]) => re.test(path))?.[1];
}

// Server components: cache the slow, stable reads so warm navigations are
// instant. Mutations go through the /api proxy, which calls clearApiCache().
const SERVER_CACHE: [RegExp, number][] = [
  [/^\/admin\/setup$/, 60_000],
  [/^\/help\/guide$/, 60_000],
  [/^\/today$/, 15_000],
  [/^\/results$/, 15_000],
  [/^\/history$/, 15_000],
  [/^\/tours$/, 30_000],
  [/^\/me$/, 30_000],
];
const serverCache = new Map<string, { at: number; value: unknown }>();

export function clearApiCache() {
  serverCache.clear();
}

function base() {
  return typeof window === "undefined" ? SERVER_BASE : "/api";
}

function csrfToken(): string {
  if (typeof document === "undefined") return "";
  const match = document.cookie.match(/(?:^|;\s*)clipdesk_csrf=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : "";
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  if (MOCK) {
    const { mockRequest } = await import("./mock");
    return mockRequest<T>(method, path, body);
  }
  const headers: Record<string, string> = {};
  if (body) headers["Content-Type"] = "application/json";
  const csrf = csrfToken();
  if (csrf) headers["X-CSRF-Token"] = csrf;
  const ttl = cacheTtl(path);
  if (method === "GET" && ttl) {
    const hit = clientCache.get(path);
    if (hit && Date.now() - hit.at < ttl) return hit.value as T;
  }
  let session = "";
  if (typeof window === "undefined") {
    const { cookies } = await import("next/headers");
    const store = await cookies();
    session = store.get("clipdesk_session")?.value ?? "";
    if (session) headers["Cookie"] = `clipdesk_session=${session}`;
  }
  const serverTtl =
    typeof window === "undefined"
      ? SERVER_CACHE.find(([re]) => re.test(path))?.[1]
      : undefined;
  if (method === "GET" && serverTtl) {
    const key = `${session}:${path}`;
    const hit = serverCache.get(key);
    if (hit && Date.now() - hit.at < serverTtl) return hit.value as T;
  }
  const res = await fetch(`${base()}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
    cache: "no-store",
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const data = await res.json();
      detail = data?.error?.message ?? data?.detail ?? JSON.stringify(data);
    } catch {
      /* keep statusText */
    }
    throw new ApiError(res.status, detail);
  }
  const data = (await res.json()) as T;
  if (method === "GET" && ttl) {
    if (clientCache.size > 200) clientCache.clear();
    clientCache.set(path, { at: Date.now(), value: data });
  }
  if (method === "GET" && serverTtl) {
    if (serverCache.size > 200) serverCache.clear();
    serverCache.set(`${session}:${path}`, { at: Date.now(), value: data });
  }
  return data;
}

const get = <T>(path: string) => request<T>("GET", path);
const post = <T>(path: string, body?: unknown) => request<T>("POST", path, body);
const patch = <T>(path: string, body?: unknown) => request<T>("PATCH", path, body);
const put = <T>(path: string, body?: unknown) => request<T>("PUT", path, body);
const del = <T>(path: string) => request<T>("DELETE", path);

export const api = {
  // --- auth -------------------------------------------------------------
  csrf: () => get<{ csrf: string }>("/auth/csrf"),
  signUp: (email: string, password: string, display_name: string, invite_code?: string) =>
    post<{ ok?: boolean }>("/auth/sign-up", { email, password, display_name, invite_code }),
  signIn: (email: string, password: string) =>
    post<{ ok?: boolean }>("/auth/sign-in", { email, password }),
  signOut: () => post<{ ok?: boolean }>("/auth/sign-out"),
  signOutAll: () => post<{ ok?: boolean }>("/auth/sign-out-all"),
  changePassword: (current_password: string, new_password: string) =>
    post<{ ok?: boolean }>("/auth/change-password", { current_password, new_password }),
  resetPassword: (token: string, new_password: string) =>
    post<{ ok?: boolean }>("/auth/reset-password", { token, new_password }),
  devSignIn: (display_name: string) =>
    post<{ ok?: boolean }>("/auth/dev/sign-in", { display_name }),
  me: () => get<{ user: Me }>("/me"),

  // --- missions --------------------------------------------------------
  today: () => get<Today>("/today"),
  accept: (mission_id: string) => post("/assignments", { mission_id }),
  swap: (id: string, mission_id: string) => post(`/assignments/${id}/swap`, { mission_id }),
  mission: (id: string) => get<PoolEntry>(`/missions/${id}`),
  updateMission: (id: string, card: MissionCard) =>
    patch(`/missions/${id}`, { card }),
  suggest: (mission_id: string) => post<Suggestion>("/ai/suggest", { mission_id }),
  missionEditor: (card: MissionCard, field: string) =>
    post<EditorResult>("/ai/mission-editor", { card, field }),

  // --- admin: pool -----------------------------------------------------
  pool: (params = "") => get<List<PoolEntry>>(`/admin/pool${params}`),
  writeCards: (questions: string[]) => post("/admin/questions", { questions }),
  approve: (id: string) => post(`/admin/pool/${id}/approve`, {}),
  reject: (id: string) => post(`/admin/pool/${id}/reject`, {}),
  assign: (id: string, user_id: string) => post(`/admin/pool/${id}/assign`, { user_id }),
  poolReview: (questions: string[]) =>
    post<{
      merged: { question: string; count: number }[];
      policy_flags: { question: string; reason: string }[];
      fallback: boolean;
    }>("/ai/pool-review", { questions }),

  // --- clips -----------------------------------------------------------
  clips: (params = "") => get<List<Clip>>(`/clips${params}`),
  clip: (id: string) => get<Clip>(`/clips/${id}`),
  updateClip: (id: string, fields: Record<string, unknown>) =>
    patch<Clip>(`/clips/${id}`, fields),
  trim: (id: string, start: number, end: number) =>
    post<{ id: string; trim_start: number; trim_end: number }>(`/clips/${id}/trim`, { start, end }),
  voiceOver: (id: string, enabled: boolean, voice?: string) =>
    post<{ id: string; voice_over: boolean; voice: string | null }>(`/clips/${id}/voice-over`, { enabled, voice }),
  voicePreview: (id: string, voice?: string) =>
    post<{ id: string; state: string }>(`/clips/${id}/voice-preview`, { voice }),
  voiceOverStatus: (id: string) => get<VoiceOver>(`/voice-overs/${id}`),
  voiceOverAudioUrl: (id: string) => `${base()}/voice-overs/${id}/audio`,
  approveClip: (id: string) => post<{ id: string; state: string }>(`/clips/${id}/approve`, {}),
  postClip: (id: string) => post<{ id: string; state: string }>(`/clips/${id}/post`, {}),
  createExport: (id: string, fields: Record<string, unknown>) =>
    post<{ id: string }>(`/clips/${id}/export`, fields),
  downloadClipUrl: (id: string) => `${base()}/clips/${id}/download`,
  downloadExportUrl: (id: string) => `${base()}/clips/${id}/export`,
  thumbnailUrl: (id: string) => `${base()}/clips/${id}/thumbnail`,
  reviewClip: (id: string) => post<ReviewResult>("/ai/clip-review", { clip_id: id }),
  exportCopy: (id: string) => post<ClipExport>("/ai/export", { clip_id: id }),

  // --- marks / streams -------------------------------------------------
  mark: (assignment_id: string, kind: "start" | "done", result?: string, stream_time?: number) =>
    post("/marks", { assignment_id, kind, result, stream_time }),
  createStream: (title: string) => post<Stream>("/streams", { title }),
  streamStatus: (id: string) => get<{ connected: boolean }>(`/streams/${id}/status`),
  obsStatus: () => get<ObsStatus>("/live/obs"),
  obsSnapshotUrl: () => `${base()}/live/obs/snapshot`,

  // --- uploads ---------------------------------------------------------
  uploadStart: () => post<{ upload_id: string; chunk_size: number }>("/uploads/start", {}),
  uploadChunk: (upload_id: string, index: number, blob: Blob) => {
    const headers: Record<string, string> = { "Content-Type": "application/octet-stream" };
    const csrf = csrfToken();
    if (csrf) headers["X-CSRF-Token"] = csrf;
    return fetch(`${base()}/uploads/${upload_id}/chunks/${index}`, {
      method: "PUT",
      headers,
      body: blob,
    }).then(async (r) => {
      if (!r.ok) throw new ApiError(r.status, await r.text());
      return r.json();
    });
  },
  uploadComplete: (upload_id: string, marks: unknown[], filename: string) =>
    post(`/uploads/${upload_id}/complete`, { marks, filename }),
  uploadStatus: (upload_id: string) => get(`/uploads/${upload_id}`),

  // --- results / history / settings ------------------------------------
  results: () => get<Results>("/results"),
  resultsSummary: () => get<{ summary: string; fallback: boolean; by_type: Results["by_type"] }>(
    "/ai/results-summary",
  ),
  recordMetric: (clip_id: string, views: number, avg_view_percentage: number) =>
    post("/metrics", { clip_id, views, avg_view_percentage }),
  history: (params = "") => get<List<HistoryEntry>>(`/history${params}`),
  settings: () => get<Settings>("/settings"),
  updateSettings: (fields: Record<string, unknown>) =>
    patch<{ ok: boolean } & Record<string, unknown>>("/settings", fields),
  deleteAccount: () => del("/account"),
  exportAccountUrl: () => `${base()}/account/export`,

  // --- ai --------------------------------------------------------------
  help: (question: string) => post<HelpAnswer>("/ai/help", { question }),
  helpGuide: () => get<{ guide: string }>("/help/guide"),

  // --- tours -----------------------------------------------------------
  tours: () => get<TourProgress[]>("/tours"),
  saveTour: (tour_id: string, step_index: number, completed: boolean, skipped: boolean) =>
    post(`/tours/${tour_id}`, { step_index, completed, skipped }),
  resetTour: (tour_id: string) => del(`/tours/${tour_id}`),

  // --- admin -----------------------------------------------------------
  adminUsers: (params = "") => get<List<User>>(`/admin/users${params}`),
  adminUpdateUser: (id: string, role: string) =>
    patch<{ id: string; role: string }>(`/admin/users/${id}`, { role }),
  adminResetLink: (id: string) => post<{ url: string }>(`/admin/users/${id}/reset-link`, {}),
  adminInvites: (params = "") => get<List<Invite>>(`/admin/invites${params}`),
  adminCreateInvite: (email?: string) =>
    post<{ id: string; code: string; url: string }>("/admin/invites", { email }),
  adminRevokeInvite: (id: string) => post(`/admin/invites/${id}/revoke`, {}),
  adminJobs: (params = "") => get<List<Job>>(`/admin/jobs${params}`),
  retryJob: (id: string) => post(`/admin/jobs/${id}/retry`, {}),
  adminAudit: (params = "") => get<List<AuditEntry>>(`/admin/audit${params}`),
  adminAiUsage: (params = "") => get<List<AiUsage>>(`/admin/ai-usage${params}`),
  adminAiConfig: () => get<AiConfig>("/admin/ai-config"),
  adminStorage: () => get<{ driver: string; bytes: number }>("/admin/storage"),
  adminSetup: () => get<{ checks: { name: string; ok: boolean; detail: string }[] }>(
    "/admin/setup",
  ),
  adminTemplates: (params = "") => get<List<unknown>>(`/admin/templates${params}`),

  // --- admin: local models -----------------------------------------------
  adminModels: () => get<ModelStatus>("/admin/models"),
  adminModelPull: (name: string) =>
    post<PullTask>("/admin/models/pull", { name }),
  adminModelPullStatus: (id: string) => get<PullTask>(`/admin/models/pull/${id}`),
  adminModelUnload: (name: string) => post<{ ok: boolean }>("/admin/models/unload", { name }),
  adminModelFree: () => post<{ ok: boolean; error?: string | null }>("/admin/models/free"),

  // --- games / research -------------------------------------------------
  games: () => get<Game[]>("/games"),
  adminGames: (params = "") => get<List<Game>>(`/admin/games${params}`),
  adminGameSearch: (query: string) =>
    post<{ results: GameSearchEntry[] }>("/admin/games/search", { query }),
  adminCreateGame: (fields: Record<string, unknown>) =>
    post<{ id: string; slug: string; name: string }>("/admin/games", fields),
  adminGame: (id: string) => get<GameProfile>(`/admin/games/${id}`),
  adminUpdateGame: (id: string, fields: Record<string, unknown>) =>
    patch<{ id: string; enabled: boolean }>(`/admin/games/${id}`, fields),
  adminRunResearch: (id: string) =>
    post<{
      run_id: string;
      game_id: string;
      sources: Record<string, number>;
      ideas: number;
      fallback: boolean;
      latency_ms: number;
    }>(`/admin/games/${id}/research`, {}),
  cardImageUrl: (id: string) => `${base()}/missions/${id}/card.svg`,

  // --- studio -----------------------------------------------------------
  studioUpload: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    const headers: Record<string, string> = {};
    const csrf = csrfToken();
    if (csrf) headers["X-CSRF-Token"] = csrf;
    return fetch(`${base()}/studio/upload`, {
      method: "POST",
      headers,
      body: form,
    }).then(async (r) => {
      if (!r.ok) throw new ApiError(r.status, await r.text());
      return r.json();
    });
  },
  studioDetect: (recording_id: string, top_n = 5) =>
    post("/studio/detect", { recording_id, top_n }),
  studioRecording: (id: string) => get<StudioRecording>(`/studio/recordings/${id}`),
  studioGenerate: (recording_id: string, mission_id: string, windows: Record<string, unknown>[]) =>
    post<{ clips: string[]; count: number }>("/studio/generate", {
      recording_id,
      mission_id,
      windows,
    }),
  studioSystem: () => get<SystemLoad>("/studio/system"),
  studioTemplates: () =>
    get<{ caption_styles: Record<string, unknown>; templates: { id: string }[] }>(
      "/studio/templates",
    ),
  studioRecordingUrl: (id: string) => `${base()}/studio/recordings/${id}/file`,
  studioSsd: () => get<SsdResponse>("/studio/ssd"),
  studioSsdImport: (path: string) =>
    post<{
      recording_id: string;
      filename: string;
      duration_seconds: number;
      width: number;
      height: number;
    }>("/studio/ssd/import", { path }),

  // --- community -------------------------------------------------------
  leaderboard: (id: string, params = "") =>
    get<List<{ rank: number; user_id: string; display_name: string; result_value: number | null; clip_id: string | null }>>(
      `/missions/${id}/leaderboard${params}`,
    ),
  publicMission: (slug: string) =>
    get<{ slug: string; card: MissionCard; attempts: unknown[] }>(`/m/${slug}`),
  creator: (id: string) =>
    get<List<{ mission_id: string; result_value: number | null; clip_id: string | null; card: { question?: string } }>>(
      `/creators/${id}`,
    ),
};
