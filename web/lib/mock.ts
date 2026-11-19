import type { Clip, HistoryEntry, MissionCard, PoolEntry } from "./types";

/**
 * Contract-shaped mock layer, enabled with NEXT_PUBLIC_API_MOCK=1.
 * Used only for screenshots; the default run never imports it.
 */

const cards: MissionCard[] = [
  {
    id: "m_0214",
    question: "Can you outrun five stars on a bicycle?",
    hook_text: "5 STARS. ONE BICYCLE.",
    setup: "Get five stars downtown, then switch to any bicycle.",
    win_condition: "Lose the wanted level without leaving the bike.",
    result_type: "time_seconds",
    est_minutes: 8,
    title_options: ["Can you escape 5 stars on a BIKE in GTA 6?"],
    mode: "free_roam",
    status: "unverified",
    evidence: { askers: 12, source_video_ids: [] },
    policy: { spoiler: false, online_exploit: false },
  },
  {
    id: "m_0215",
    question: "Can you win a street race without using the brakes?",
    hook_text: "NO BRAKES. NO PROBLEM.",
    setup: "Enter any street race and never touch the brake.",
    win_condition: "Win the race without pressing the brake.",
    result_type: "time_seconds",
    est_minutes: 5,
    title_options: ["Winning a race with NO BRAKES"],
    mode: "race",
    status: "unverified",
    evidence: { askers: 7, source_video_ids: [] },
    policy: { spoiler: false, online_exploit: false },
  },
  {
    id: "m_0216",
    question: "Can you survive a five-star wanted level on foot?",
    hook_text: "FIVE STARS, NO CAR.",
    setup: "Start on foot with a five-star wanted level.",
    win_condition: "Survive for three minutes without a vehicle.",
    result_type: "time_seconds",
    est_minutes: 3,
    title_options: ["5 stars, no car, no chance?"],
    mode: "free_roam",
    status: "unverified",
    evidence: { askers: 4, source_video_ids: [] },
    policy: { spoiler: false, online_exploit: false },
  },
];

let pool: PoolEntry[] = [
  {
    id: "m_0301",
    card: { ...cards[0], id: "m_0301", question: "Can you swim across the whole map?" },
    score: 0,
    state: "candidate",
  },
];

const clips: Clip[] = [
  {
    id: "c_0001",
    assignment_id: "a_0001",
    file_key: "clips/c_0001/short.mp4",
    title: "5 STARS. ONE BICYCLE.",
    state: "ready",
    template: "blur_fit",
    duration_seconds: 29.1,
    stage: "store",
    progress: 100,
    error: null,
    layout: "blur_fit",
    caption_style: "word",
    voice_over: false,
    voice: null,
    export_title: null,
    export_description: null,
    export_tags: null,
    transcript: [],
    download_url: "/clips/c_0001/download",
  },
  {
    id: "c_0002",
    assignment_id: "a_0002",
    file_key: null,
    title: "NO BRAKES. NO PROBLEM.",
    state: "rendering",
    template: "center_crop",
    duration_seconds: null,
    stage: "render",
    progress: 62,
    error: null,
    layout: "center_crop",
    caption_style: "word",
    voice_over: false,
    voice: null,
    export_title: null,
    export_description: null,
    export_tags: null,
    transcript: null,
    download_url: null,
  },
];

const history: HistoryEntry[] = [
  { mission_id: "m_0214", date: "2026-11-16", state: "done", result_value: 41.2, clip_id: "c_0001", clip_state: "ready", duration_seconds: 29.1 },
  { mission_id: "m_0215", date: "2026-11-15", state: "done", result_value: 55.8, clip_id: "c_0002", clip_state: "rendering", duration_seconds: null },
];

function envelope<T>(items: T[], total = items.length) {
  return { items, total, page: 1, page_size: 20 };
}

export async function mockRequest<T>(method: string, path: string, body?: unknown): Promise<T> {
  const [pathname] = path.split("?");
  const bodyObj = (body ?? {}) as Record<string, unknown>;

  if (method === "GET" && pathname === "/today") {
    return {
      date: new Date().toISOString().slice(0, 10),
      daily: cards[0],
      picks: cards.slice(1, 4),
      accepted: {},
    } as T;
  }
  if (method === "GET" && pathname === "/me") {
    // Admin so the admin pages render for screenshots; the creator pages render too.
    return { user: { id: "u_1", email: "admin@example.com", display_name: "Dev Admin", role: "admin" }, channels: [] } as T;
  }
  if (method === "POST" && pathname === "/auth/dev/sign-in") return { ok: true } as T;
  if (method === "POST" && pathname === "/auth/sign-in") return { ok: true } as T;
  if (method === "POST" && pathname === "/auth/sign-up") return { ok: true } as T;
  if (method === "POST" && pathname === "/assignments") {
    return { id: "a_new", mission_id: bodyObj.mission_id, state: "accepted" } as T;
  }
  if (method === "POST" && pathname.endsWith("/swap")) {
    return { id: pathname.split("/")[2], mission_id: bodyObj.mission_id, state: "swapped" } as T;
  }
  if (method === "GET" && pathname === "/admin/pool") return envelope(pool) as T;
  if (method === "POST" && pathname.endsWith("/approve")) {
    const id = pathname.split("/")[3];
    pool = pool.filter((p) => p.id !== id);
    return { id, state: "unverified" } as T;
  }
  if (method === "POST" && pathname === "/admin/questions") {
    const questions = (bodyObj.questions as string[]) ?? [];
    const created: PoolEntry[] = questions.map((q, i) => ({
      id: `m_${400 + i}`,
      card: { ...cards[i % cards.length], id: `m_${400 + i}`, question: q },
      score: 0,
      state: "candidate",
    }));
    pool = [...pool, ...created];
    return { cards: created.map((c) => c.card), count: created.length, fallback: false } as T;
  }
  if (method === "GET" && pathname === "/clips") return envelope(clips) as T;
  if (method === "GET" && pathname.startsWith("/clips/")) return clips[0] as T;
  if (method === "PATCH" && pathname.startsWith("/clips/")) {
    const id = pathname.split("/")[2];
    const clip = clips.find((c) => c.id === id);
    if (clip) clip.title = String(bodyObj.title ?? clip.title);
    return clip as T;
  }
  if (method === "POST" && pathname.endsWith("/approve")) return { id: pathname.split("/")[2], state: "approved" } as T;
  if (method === "POST" && pathname.endsWith("/post")) return { id: pathname.split("/")[2], state: "posted" } as T;
  if (method === "POST" && pathname.endsWith("/trim")) return { id: pathname.split("/")[2], ...bodyObj } as T;
  if (method === "POST" && pathname.endsWith("/voice-over")) return { id: pathname.split("/")[2], ...bodyObj } as T;
  if (method === "POST" && pathname.endsWith("/export")) return { id: "e_1", state: "ready" } as T;
  if (method === "POST" && pathname === "/marks") {
    return { id: "mk_1", assignment_id: String(bodyObj.assignment_id ?? ""), kind: String(bodyObj.kind), stream_time: 12.5, result: null } as T;
  }
  if (method === "POST" && pathname === "/streams") {
    return { id: "s_1", rtmp_url: "rtmp://localhost:1935/live", stream_key: "dev-key-please-change" } as T;
  }
  if (method === "GET" && pathname.endsWith("/status")) return { connected: true } as T;
  if (method === "POST" && pathname === "/uploads/start") return { upload_id: "u_1", chunk_size: 1048576 } as T;
  if (method === "POST" && pathname.endsWith("/complete")) return { stream_id: "s_1", clips: [], count: 0 } as T;
  if (method === "GET" && pathname.endsWith("/leaderboard")) {
    return envelope([
      { rank: 1, user_id: "u_1", result_value: 41.2, clip_id: "c_0001" },
      { rank: 2, user_id: "u_2", result_value: 55.8, clip_id: "c_0003" },
    ]) as T;
  }
  if (method === "GET" && pathname.startsWith("/m/")) {
    return { slug: pathname.slice(3), card: cards[0], attempts: [] } as T;
  }
  if (method === "GET" && pathname === "/results") {
    return {
      clips: [
        { clip_id: "c_0001", title: "5 STARS. ONE BICYCLE.", views: 1204, avg_view_percentage: 61.2, source: "manual" },
        { clip_id: "c_0002", title: "NO BRAKES. NO PROBLEM.", views: 842, avg_view_percentage: 55.7, source: "manual" },
      ],
      by_type: [
        { mode: "free_roam", clips: 8, views: 9820 },
        { mode: "race", clips: 3, views: 2140 },
      ],
    } as T;
  }
  if (method === "GET" && pathname === "/history") return envelope(history) as T;
  if (method === "GET" && pathname === "/settings") {
    return {
      plan: "free",
      clips_used: 3,
      clips_limit: 5,
      caption_style: "word",
      layout_preference: "rotate",
      voice_over_default: false,
      voice: null,
    } as T;
  }
  if (method === "PATCH" && pathname === "/settings") return { ok: true, ...bodyObj } as T;
  if (method === "GET" && pathname === "/admin/users") {
    return envelope([
      { id: "u_1", email: "creator@example.com", display_name: "Creator", role: "creator", created_at: "2026-11-01T00:00:00Z", last_login_at: null, locked: false },
    ]) as T;
  }
  if (method === "GET" && pathname === "/admin/invites") return envelope([]) as T;
  if (method === "POST" && pathname === "/admin/invites") {
    return { id: "i_1", code: "mock-code", url: "/signup?code=mock-code" } as T;
  }
  if (method === "GET" && pathname === "/admin/jobs") return envelope([]) as T;
  if (method === "GET" && pathname === "/admin/audit") return envelope([]) as T;
  if (method === "GET" && pathname === "/admin/ai-usage") return envelope([]) as T;
  if (method === "GET" && pathname === "/admin/ai-config") {
    return { provider: "recorded", base_url: "https://example.invalid/v1", model: "recorded", key_present: false, configured: false } as T;
  }
  if (method === "GET" && pathname === "/admin/models") {
    return {
      bridge: "up",
      error: null,
      provider: {
        llm_provider: "openai",
        llm_model: "qwen3:8b",
        llm_base_url: "http://localhost:11434/v1",
        configured: true,
        asr: "mlx",
        mlx_model: "mlx-community/whisper-large-v3-mlx",
      },
      engine: {
        compute: "mlx-metal",
        model: "mlx-community/whisper-large-v3-mlx",
        ollama: {
          available: true,
          error: null,
          models: [
            { name: "qwen3:8b", size_bytes: 8_000_000_000, modified_at: "2026-11-01T00:00:00Z" },
            { name: "qwen2.5-coder:14b", size_bytes: 9_000_000_000, modified_at: "2026-11-01T00:00:00Z" },
          ],
          running: [
            { name: "qwen3:8b", size_bytes: 8_000_000_000, size_vram_bytes: 6_000_000_000, expires_at: null },
          ],
        },
        mlx: {
          model: "mlx-community/whisper-large-v3-mlx",
          transcribing: false,
          last_elapsed_s: 30.2,
          peak_memory_bytes: 2_000_000_000,
          downloaded: true,
          error: null,
        },
        host: { total_bytes: 32_000_000_000, used_bytes: 20_000_000_000, percent: 62.5 },
      },
    } as T;
  }
  if (method === "POST" && pathname === "/admin/models/pull") {
    return { id: "t_1", name: bodyObj.name, done: true, progress: 100, status: "done", error: null } as T;
  }
  if (method === "POST" && pathname === "/admin/models/unload") return { ok: true } as T;
  if (method === "POST" && pathname === "/admin/models/free") return { ok: true } as T;
  if (method === "GET" && pathname === "/admin/calendar") {
    return {
      month: "2026-11",
      entries: [
        { id: "ce_1", clip_id: "c_0001", date: "2026-11-20", platform: "youtube", state: "draft", title: "5 stars, one bicycle", duration_seconds: 24 },
      ],
      unscheduled: [{ id: "c_0002", title: "Clutch no-scope", duration_seconds: 18 }],
      warnings: [],
      daily_limit: 2,
      platforms: { youtube: "YouTube", tiktok: "TikTok (approval required)", instagram: "Instagram (approval required)" },
      gated: ["tiktok", "instagram"],
    } as T;
  }
  if (method === "POST" && pathname === "/admin/calendar") return { ok: true } as T;
  if (method === "POST" && pathname.endsWith("/publish")) return { ok: true, unproven: "youtube-api" } as T;
  if (method === "DELETE" && pathname.startsWith("/admin/calendar/")) return { ok: true } as T;
  if (method === "GET" && pathname === "/admin/clips") {
    return {
      items: [
        { id: "c_0001", title: "5 stars, one bicycle", state: "approved", duration_seconds: 24, created_at: "2026-11-01T00:00:00Z" },
        { id: "c_0002", title: "Clutch no-scope", state: "approved", duration_seconds: 18, created_at: "2026-11-02T00:00:00Z" },
      ],
    } as T;
  }
  if (method === "GET" && pathname === "/admin/long-form") return { items: [] } as T;
  if (method === "POST" && pathname === "/admin/long-form") return { id: "lf_1", state: "queued" } as T;
  if (method === "GET" && pathname === "/admin/provider") {
    return {
      env: { llm_provider: "openai", llm_model: "qwen3:8b", llm_base_url: "http://localhost:11434/v1", configured: true },
      stored: {},
      effective: { llm_provider: "openai", llm_model: "qwen3:8b", llm_base_url: "http://localhost:11434/v1", asr: "mlx" },
    } as T;
  }
  if (method === "POST" && pathname === "/admin/provider") return { ok: true } as T;
  if (method === "GET" && pathname === "/admin/storage") return { driver: "local", bytes: 123456 } as T;
  if (method === "GET" && pathname === "/studio/system") {
    return { cpu_percent: 12.5, memory_percent: 41.2, gpu: null } as T;
  }
  if (method === "GET" && pathname === "/admin/setup") {
    return { checks: [
      { name: "DATABASE_URL set", ok: true, detail: "" },
      { name: "storage (local)", ok: true, detail: "" },
    ] } as T;
  }
  if (method === "GET" && pathname === "/admin/templates") return envelope([]) as T;
  if (method === "GET" && pathname === "/tours") {
    return [
      { tour_id: "creator", step_index: 6, completed: true, skipped: false },
      { tour_id: "admin", step_index: 5, completed: true, skipped: false },
    ] as T;
  }
  if (method === "POST" && pathname.startsWith("/tours/")) return { ok: true } as T;
  if (method === "GET" && pathname === "/ai/results-summary") {
    return { summary: "Free-roam missions are working best.", fallback: false, by_type: [] } as T;
  }
  if (method === "POST" && pathname === "/ai/suggest") {
    return { suggestions: cards.slice(1, 4), fallback: false } as T;
  }
  if (method === "POST" && pathname === "/ai/mission-editor") {
    return { hook_text: "5 STARS. ONE BICYCLE.", win_condition: "Lose the wanted level without leaving the bike.", title_spoiler: false, fallback: false } as T;
  }
  if (method === "POST" && pathname === "/ai/clip-review") {
    return { hook_line: "5 STARS. ONE BICYCLE.", score: 82, weaknesses: [], beats: [], fallback: false } as T;
  }
  if (method === "POST" && pathname === "/ai/export") {
    return { titles: ["Title one", "Title two", "Title three"], description: "A description", tags: ["one"], fallback: false } as T;
  }
  if (method === "POST" && pathname === "/ai/pool-review") {
    return { merged: [], policy_flags: [], fallback: false } as T;
  }
  if (method === "POST" && pathname === "/ai/help") {
    return { answer: "Open Today and accept a mission.", fallback: false } as T;
  }
  if (method === "GET" && pathname === "/help/guide") return { guide: "# Guide\n" } as T;
  return { ok: true } as T;
}
