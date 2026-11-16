import type { MissionCard, PoolEntry } from "./types";

/**
 * Contract-shaped mock layer, enabled with NEXT_PUBLIC_API_MOCK=1.
 * Every page that uses it is listed under "Mocked pages" in PROGRESS.md.
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

const clips = [
  {
    id: "c_0001",
    assignment_id: "a_0001",
    title: "5 STARS. ONE BICYCLE.",
    state: "ready",
    template: "blur_fit",
    duration_seconds: 29.1,
    download_url: "/downloads/c_0001.mp4",
  },
  {
    id: "c_0002",
    assignment_id: "a_0002",
    title: "NO BRAKES. NO PROBLEM.",
    state: "rendering",
    template: "center_crop",
    duration_seconds: null,
    download_url: null,
  },
];

const marks: { id: string; assignment_id: string; kind: string; stream_time: number }[] = [];
let stream: { id: string; rtmp_url: string; stream_key: string } | null = null;

function json<T>(data: T, status = 200): T {
  return data;
}

export async function mockRequest<T>(method: string, path: string, body?: unknown): Promise<T> {
  const [pathname] = path.split("?");
  const bodyObj = (body ?? {}) as Record<string, unknown>;

  if (method === "GET" && pathname === "/today") {
    return json({
      date: new Date().toISOString().slice(0, 10),
      daily: cards[0],
      picks: cards.slice(1, 4),
      accepted: {},
    }) as T;
  }
  if (method === "GET" && pathname === "/me") {
    return json({ user: { id: "u_1", display_name: "Dev Creator", role: "creator" }, channels: [] }) as T;
  }
  if (method === "POST" && pathname === "/assignments") {
    return json({ id: "a_new", mission_id: bodyObj.mission_id, state: "accepted" }) as T;
  }
  if (method === "POST" && pathname.endsWith("/swap")) {
    return json({ id: pathname.split("/")[2], mission_id: bodyObj.mission_id, state: "swapped" }) as T;
  }
  if (method === "GET" && pathname === "/admin/pool") {
    return json(pool) as T;
  }
  if (method === "POST" && pathname.endsWith("/approve")) {
    const id = pathname.split("/")[3];
    pool = pool.filter((p) => p.id !== id);
    return json({ id, state: "unverified" }) as T;
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
    return json({ cards: created.map((c) => c.card), count: created.length }) as T;
  }
  if (method === "GET" && pathname === "/clips") {
    return json(clips) as T;
  }
  if (method === "PATCH" && pathname.startsWith("/clips/")) {
    const id = pathname.split("/")[2];
    const clip = clips.find((c) => c.id === id);
    if (clip) clip.title = String(bodyObj.title ?? clip.title);
    return json(clip ?? {}) as T;
  }
  if (method === "POST" && pathname.endsWith("/approve")) {
    return json({ id: pathname.split("/")[2], state: "approved" }) as T;
  }
  if (method === "POST" && pathname.endsWith("/post")) {
    return json({ id: "p_new", clip_id: pathname.split("/")[2], state: "posted" }) as T;
  }
  if (method === "POST" && pathname === "/marks") {
    const mark = {
      id: `mk_${marks.length + 1}`,
      assignment_id: String(bodyObj.assignment_id ?? ""),
      kind: String(bodyObj.kind),
      stream_time: 12.5,
      result: (bodyObj.result as string) ?? null,
    };
    marks.push(mark);
    return json(mark) as T;
  }
  if (method === "POST" && pathname === "/streams") {
    stream = {
      id: "s_1",
      rtmp_url: "rtmp://localhost:1935/live",
      stream_key: "dev-key-please-change",
    };
    return json(stream) as T;
  }
  if (method === "GET" && pathname.endsWith("/leaderboard")) {
    return json([
      { rank: 1, user_id: "u_1", result_value: 41.2, clip_id: "c_0001" },
      { rank: 2, user_id: "u_2", result_value: 55.8, clip_id: "c_0003" },
    ]) as T;
  }
  if (method === "GET" && pathname.startsWith("/m/")) {
    return json({ slug: pathname.slice(3), card: cards[0], attempts: [] }) as T;
  }
  if (method === "GET" && pathname === "/results") {
    return json({
      clips: [
        { clip_id: "c_0001", title: "5 STARS. ONE BICYCLE.", views: 1204, avg_view_percentage: 61.2 },
        { clip_id: "c_0002", title: "NO BRAKES. NO PROBLEM.", views: 842, avg_view_percentage: 55.7 },
      ],
      by_type: [
        { mode: "free_roam", clips: 8, views: 9820 },
        { mode: "race", clips: 3, views: 2140 },
      ],
    }) as T;
  }
  if (method === "GET" && pathname === "/history") {
    return json([
      { mission_id: "m_0214", date: "2026-11-16", state: "done", result_value: 41.2, clip_id: "c_0001" },
      { mission_id: "m_0215", date: "2026-11-15", state: "done", result_value: 55.8, clip_id: "c_0002" },
    ]) as T;
  }
  if (method === "GET" && pathname === "/settings") {
    return json({
      plan: "free",
      clips_used: 3,
      clips_limit: 5,
      caption_style: "word",
      layout_preference: "rotate",
    }) as T;
  }
  return json({ ok: true }) as T;
}
