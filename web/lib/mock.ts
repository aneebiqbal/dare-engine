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
      effective: { llm_provider: "openai", llm_model: "qwen3:8b", llm_base_url: "http://localhost:11434/v1", asr: "mlx", configured: true },
    } as T;
  }
  if (method === "POST" && pathname === "/admin/provider") return { ok: true } as T;
  if (method === "GET" && pathname === "/admin/storage") return { driver: "local", bytes: 123456 } as T;
  if (method === "GET" && pathname === "/admin/errors") return { items: [] } as T;
  if (method === "GET" && pathname === "/admin/keys") {
    return {
      research_sources_configured: true,
      integrations: [
        { name: "youtube", label: "YouTube Data API", group: "Research sources", docs: "https://console.cloud.google.com/apis/credentials", env_var: "youtube_api_key", masked: "AIz...7890", configured: true, source: "env", status: "connected", status_detail: "YouTube Data API v3 accepted the key.", tested_at: "2026-11-23T00:00:00Z" },
        { name: "reddit_client", label: "Reddit client ID", group: "Research sources", docs: "https://www.reddit.com/prefs/apps", env_var: "reddit_client_id", masked: "", configured: false, source: "none", status: "untested", status_detail: null, tested_at: null },
        { name: "reddit_secret", label: "Reddit client secret", group: "Research sources", docs: "https://www.reddit.com/prefs/apps", env_var: "reddit_client_secret", masked: "", configured: false, source: "none", status: "untested", status_detail: null, tested_at: null },
        { name: "rawg", label: "RAWG game database", group: "Research sources", docs: "https://rawg.io/apidocs", env_var: "rawg_api_key", masked: "raw...key", configured: true, source: "env", status: "connected", status_detail: "RAWG accepted the key.", tested_at: "2026-11-23T00:00:00Z" },
        { name: "llm", label: "AI provider key", group: "AI", docs: "https://opencode.ai/zen", env_var: "llm_api_key", masked: "sk-...4f2a", configured: true, source: "stored", status: "connected", status_detail: "model answered a test call.", tested_at: "2026-11-23T00:00:00Z" },
      ],
    } as T;
  }
  if (method === "POST" && pathname === "/admin/keys") return { ok: true, name: "youtube", masked: "AIz...7890" } as T;
  if (method === "DELETE" && pathname.startsWith("/admin/keys/")) return { ok: true } as T;
  if (method === "POST" && pathname === "/admin/keys/test") return { ok: true, status: "connected", detail: "YouTube Data API v3 accepted the key." } as T;
  if (method === "GET" && pathname === "/studio/system") {
    return { cpu_percent: 12.5, memory_percent: 41.2, gpu: null } as T;
  }
  if (method === "GET" && pathname === "/studio/recordings") return { items: [] } as T;
  if (method === "GET" && pathname === "/projects") {
    return {
      items: [
        {
          id: "p_1",
          name: "gameplay_4min.mp4",
          game_id: null,
          recording_id: "r_1",
          stream_id: null,
          vision: true,
          stage: "analyzing",
          stage_index: 3,
          progress: 50,
          stage_note: "Analysis complete: 5 candidates.",
          candidates: 5,
          clips: { ready: 0, total: 0, reviewed: 0 },
          queued: false,
          queue_position: null,
          created_at: "2026-11-23T00:00:00Z",
          updated_at: "2026-11-23T00:00:00Z",
        },
      ],
    } as T;
  }
  if (method === "POST" && pathname === "/projects") {
    return {
      id: "p_2",
      name: bodyObj.name ?? "Untitled project",
      game_id: bodyObj.game_id ?? null,
      recording_id: null,
      stream_id: null,
      vision: false,
      stage: "planned",
      stage_index: 0,
      progress: 0,
      stage_note: null,
      candidates: 0,
      clips: { ready: 0, total: 0, reviewed: 0 },
      queued: false,
      queue_position: null,
      created_at: "2026-11-23T00:00:00Z",
      updated_at: "2026-11-23T00:00:00Z",
    } as T;
  }
  if (method === "POST" && pathname.endsWith("/queue")) {
    return { queued: true, project_id: pathname.split("/")[2], state: null } as T;
  }
  if (method === "POST" && pathname.endsWith("/vision")) return { ok: true, ...bodyObj } as T;
  if (method === "POST" && pathname.endsWith("/attach")) return { ok: true } as T;
  if (method === "DELETE" && pathname.startsWith("/projects/")) return { deleted: true } as T;
  if (method === "GET" && pathname === "/admin/wizard") {
    return {
      steps: [
        { id: "ssd", title: "Connect the SSD", body: "", help: "", status: "done", detail: "1 drive(s) connected", updated_at: "2026-11-23T00:00:00Z" },
        { id: "obs", title: "Connect OBS over the network", body: "", help: "", status: "done", detail: "Connected to OBS 33.0.1", updated_at: "2026-11-23T00:00:00Z" },
        { id: "models", title: "Install the local models", body: "", help: "", status: "pending", detail: null, updated_at: null },
        { id: "cloud", title: "Connect the cloud account and AI provider", body: "", help: "", status: "pending", detail: null, updated_at: null },
      ],
      ready: false,
      next: "models",
    } as T;
  }
  if (method === "GET" && pathname === "/admin/engine-events") {
    return {
      items: [
        { id: "e_1", kind: "model_load", detail: "whisper mlx/metal", created_at: "2026-11-23T00:00:00Z" },
        { id: "e_2", kind: "model_unload", detail: "whisper", created_at: "2026-11-23T00:00:05Z" },
        { id: "e_3", kind: "cleanup", detail: "render_clip abc", created_at: "2026-11-23T00:00:10Z" },
      ],
    } as T;
  }
  if (method === "POST" && pathname.startsWith("/admin/wizard/")) {
    return { steps: [], ready: false, next: null } as T;
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

  // --- redesign: live overview, research runs, pool bulk -------------------
  if (method === "GET" && pathname === "/admin/overview") {
    return {
      generated_at: "2026-11-23T00:00:00Z",
      jobs: {
        counts: { queued: 2, running: 1, done: 40, failed: 1 },
        running: 3,
        failed: 1,
        active: [
          { id: "j_1", kind: "detect_moments", state: "running", stage: "transcribe", error: null, updated_at: "2026-11-23T00:00:00Z" },
          { id: "j_2", kind: "render_clip", state: "queued", stage: null, error: null, updated_at: "2026-11-23T00:00:00Z" },
          { id: "j_3", kind: "render_clip", state: "failed", stage: "render", error: "encoder missing", updated_at: "2026-11-23T00:00:00Z" },
        ],
      },
      research: {
        active: [
          { id: "rr_1", game_id: "g_1", game_name: "Grand Theft Auto V", status: "running", stage: "write", detail: "5 sources fetched — the AI is writing ideas…", source_counts: { youtube: 2, reddit: 2, news: 1 }, ideas_count: 0, fallback: false, error: null, created_at: "2026-11-23T00:00:00Z", finished_at: null },
        ],
        recent: [
          { id: "rr_1", game_id: "g_1", game_name: "Grand Theft Auto V", status: "running", stage: "write", detail: "5 sources fetched — the AI is writing ideas…", source_counts: { youtube: 2, reddit: 2, news: 1 }, ideas_count: 0, fallback: false, error: null, created_at: "2026-11-23T00:00:00Z", finished_at: null },
          { id: "rr_0", game_id: "g_1", game_name: "Grand Theft Auto V", status: "done", stage: null, detail: null, source_counts: { youtube: 2, reddit: 2, news: 1 }, ideas_count: 3, fallback: true, error: null, created_at: "2026-11-22T00:00:00Z", finished_at: "2026-11-22T00:00:05Z" },
        ],
      },
      projects: [
        { id: "p_1", name: "Friday stream — GTA", game_id: null, recording_id: "r_1", stream_id: null, vision: true, stage: "analyzing", stage_index: 3, progress: 50, stage_note: "Detection complete: 5 candidates.", candidates: 5, clips: { ready: 0, total: 0, reviewed: 0 }, queued: true, queue_position: 1, created_at: "2026-11-23T00:00:00Z", updated_at: "2026-11-23T00:00:00Z" },
        { id: "p_2", name: "Sunday session", game_id: null, recording_id: "r_2", stream_id: null, vision: false, stage: "clips_ready", stage_index: 4, progress: 75, stage_note: "3 clips ready.", candidates: 4, clips: { ready: 3, total: 3, reviewed: 1 }, queued: false, queue_position: null, created_at: "2026-11-21T00:00:00Z", updated_at: "2026-11-21T00:00:00Z" },
      ],
      pool: { candidate: 4, unverified: 2, rejected: 1 },
      keys: {
        research_sources_configured: true,
        failing: [],
        unreachable: [],
        integrations: [
          { name: "youtube", label: "YouTube Data API", group: "Research sources", docs: "https://console.cloud.google.com/apis/credentials", env_var: "youtube_api_key", masked: "AIz...7890", configured: true, source: "env", status: "connected", status_detail: "accepted", tested_at: "2026-11-23T00:00:00Z" },
          { name: "reddit_client", label: "Reddit client ID", group: "Research sources", docs: "https://www.reddit.com/prefs/apps", env_var: "reddit_client_id", masked: "", configured: false, source: "none", status: "untested", status_detail: null, tested_at: null },
          { name: "reddit_secret", label: "Reddit client secret", group: "Research sources", docs: "https://www.reddit.com/prefs/apps", env_var: "reddit_client_secret", masked: "", configured: false, source: "none", status: "untested", status_detail: null, tested_at: null },
          { name: "rawg", label: "RAWG game database", group: "Research sources", docs: "https://rawg.io/apidocs", env_var: "rawg_api_key", masked: "raw...key", configured: true, source: "env", status: "connected", status_detail: "accepted", tested_at: "2026-11-23T00:00:00Z" },
          { name: "llm", label: "AI provider key", group: "AI", docs: "https://opencode.ai/zen", env_var: "llm_api_key", masked: "sk-...4f2a", configured: true, source: "stored", status: "connected", status_detail: "answered", tested_at: "2026-11-23T00:00:00Z" },
        ],
      },
      system: { cpu_percent: 22, memory_percent: 58, gpu: null },
      activity: [
        { id: "e_1", kind: "model_load", detail: "whisper mlx/metal", created_at: "2026-11-23T00:00:00Z" },
        { id: "e_2", kind: "job_start", detail: "detect_moments", created_at: "2026-11-23T00:00:01Z" },
      ],
      results: {
        best: { clip_id: "c_0001", title: "5 STARS. ONE BICYCLE.", views: 1204, avg_view_percentage: 61.2, swiped: 300, saves: 40 },
        worst: { clip_id: "c_0002", title: "NO BRAKES. NO PROBLEM.", views: 842, avg_view_percentage: 38.1, swiped: 400, saves: 12 },
        total_views: 2046,
      },
      clips_today: 2,
      users: { total: 3, admins: 1, locked: 0 },
      invites: { open: 2 },
      storage: { driver: "local", bytes: 123456 },
    } as T;
  }
  if (method === "GET" && pathname === "/admin/research/rr_1") {
    return {
      id: "rr_1", game_id: "g_1", game_name: "Grand Theft Auto V", status: "running",
      stage: "write", detail: "5 sources fetched — the AI is writing ideas…",
      source_counts: { youtube: 2, reddit: 2, news: 1 }, ideas_count: 0, fallback: false,
      error: null, created_at: "2026-11-23T00:00:00Z", finished_at: null,
    } as T;
  }
  if (method === "POST" && pathname.endsWith("/research")) {
    return { run_id: "rr_1", status: "running", stage: "queued" } as T;
  }
  if (method === "POST" && pathname === "/admin/pool/bulk") {
    const ids = (bodyObj.ids as string[]) ?? [];
    pool = pool.filter((p) => !ids.includes(p.id));
    return { updated: ids.length } as T;
  }
  if (method === "GET" && pathname === "/admin/games") {
    return envelope([
      { id: "g_1", slug: "grand-theft-auto-v", name: "Grand Theft Auto V", external_id: "9724", source: "rawg", genre: "Action", release_date: "2013-09-17", art_url: null, enabled: true, created_at: "2026-11-01T00:00:00Z", candidates: 4, approved: 2, gamers: 1, last_run: { id: "rr_1", status: "running", stage: "write", detail: "writing…", ideas_count: 0, fallback: false, created_at: "2026-11-23T00:00:00Z" } },
      { id: "g_2", slug: "gta-6", name: "Grand Theft Auto VI", external_id: "0", source: "rawg", genre: "Action", release_date: null, art_url: null, enabled: false, created_at: "2026-11-02T00:00:00Z", candidates: 0, approved: 0, gamers: 0, last_run: null },
    ]) as T;
  }
  if (method === "GET" && pathname.startsWith("/admin/games/")) {
    return {
      game: { id: "g_1", slug: "grand-theft-auto-v", name: "Grand Theft Auto V", external_id: "9724", source: "rawg", genre: "Action", release_date: "2013-09-17", art_url: null, enabled: true, created_at: "2026-11-01T00:00:00Z" },
      candidates: [
        { id: "m_0301", card: { ...cards[0], id: "m_0301" }, score: 0.62, state: "candidate", sources: [{ kind: "youtube", title: "GTA V gameplay", url: "https://www.youtube.com/watch?v=1", external_id: "1", published_at: null }] },
        { id: "m_0302", card: { ...cards[1], id: "m_0302" }, score: 0.41, state: "candidate", sources: [] },
      ],
      approved: [{ id: "m_0303", card: { ...cards[2], id: "m_0303" }, score: 0.55, state: "unverified", sources: [] }],
      assigned: [],
      runs: [
        { id: "rr_1", status: "running", stage: "write", detail: "5 sources fetched — the AI is writing ideas…", source_counts: { youtube: 2, reddit: 2, news: 1 }, ideas_count: 0, fallback: false, error: null, created_at: "2026-11-23T00:00:00Z", finished_at: null },
      ],
    } as T;
  }
  if (method === "GET" && pathname === "/studio/recordings/r_1") {
    return {
      recording: { id: "r_1", filename: "gameplay_4min.mp4", duration_seconds: 290.2, width: 1920, height: 1080 },
      compute: { whisper_device: "mlx", whisper_compute_type: "metal", encoder: "h264_videotoolbox", gpu: true },
      vision: { model: "qwen2.5vl:7b", seconds_added: 45 },
      job: { kind: "detect_moments", state: "running", stage: "detect" },
      candidates: [
        { id: "sc_1", start: 240, end: 252, score: 6.91, reasons: ["commentary", "fast cuts"], state: "pending", template_id: "cold_open", clip_id: null, source: "audio", thumb_url: null },
        { id: "sc_2", start: 94, end: 106, score: 5.8, reasons: ["vision", "striking frame"], state: "accepted", template_id: "center", clip_id: "c_0002", source: "vision", thumb_url: null },
      ],
    } as T;
  }
  if (method === "POST" && pathname === "/studio/detect") return { ok: true } as T;
  if (method === "POST" && pathname === "/studio/vision") return { ok: true } as T;
  if (method === "POST" && pathname === "/studio/generate") return { clips: ["c_0002"], count: 1 } as T;
  if (method === "GET" && pathname === "/studio/templates") {
    return { templates: [{ id: "cold_open" }, { id: "center" }], caption_styles: { word: {}, line: {}, pop: {} } } as T;
  }
  if (method === "GET" && pathname === "/studio/ssd") {
    return { enabled: true, reason: null, error: null, drives: [{ path: "/Volumes/TestSSD", name: "TestSSD", error: null, videos: [{ path: "/Volumes/TestSSD/gameplay.mp4", name: "gameplay.mp4", size_bytes: 33_000_000, duration_seconds: 291.8, width: 1280, height: 720, error: null }] }] } as T;
  }
  if (method === "POST" && pathname === "/studio/ssd/import") {
    return { recording_id: "r_1", filename: "gameplay.mp4", duration_seconds: 291.8, width: 1280, height: 720, released: true } as T;
  }
  return { ok: true } as T;
}
