import type {
  Attempt,
  Clip,
  HistoryEntry,
  Mark,
  Me,
  PoolEntry,
  Results,
  Settings,
  Stream,
  Today,
} from "./types";

export type {
  Attempt,
  Clip,
  HistoryEntry,
  Mark,
  Me,
  MissionCard,
  PoolEntry,
  Results,
  Settings,
  Stream,
  Today,
} from "./types";

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

const SERVER_BASE = process.env.API_URL ?? "http://api:8000";
export const MOCK = process.env.NEXT_PUBLIC_API_MOCK === "1";

function base() {
  // The browser talks to our own same-origin proxy; the server talks to the API.
  return typeof window === "undefined" ? SERVER_BASE : "/api";
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  if (MOCK) {
    const { mockRequest } = await import("./mock");
    return mockRequest<T>(method, path, body);
  }
  const headers: Record<string, string> = {};
  if (body) headers["Content-Type"] = "application/json";
  if (typeof window === "undefined") {
    const { cookies } = await import("next/headers");
    const store = await cookies();
    const token = store.get("clipdesk_session")?.value;
    if (token) headers["Cookie"] = `clipdesk_session=${token}`;
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
      detail = JSON.stringify(await res.json());
    } catch {
      /* keep statusText */
    }
    throw new ApiError(res.status, detail);
  }
  return (await res.json()) as T;
}

export const api = {
  today: () => request<Today>("GET", "/today"),
  me: () => request<Me>("GET", "/me"),
  accept: (mission_id: string) =>
    request("POST", "/assignments", { mission_id }),
  swap: (id: string, mission_id: string) =>
    request("POST", `/assignments/${id}/swap`, { mission_id }),
  pool: () => request<PoolEntry[]>("GET", "/admin/pool"),
  approve: (id: string) => request("POST", `/admin/pool/${id}/approve`),
  writeCards: (questions: string[]) =>
    request("POST", "/admin/questions", { questions }),
  clips: () => request<Clip[]>("GET", "/clips"),
  retitleClip: (id: string, title: string) =>
    request("PATCH", `/clips/${id}`, { title }),
  approveClip: (id: string) => request("POST", `/clips/${id}/approve`),
  postClip: (id: string) => request("POST", `/clips/${id}/post`),
  mark: (assignment_id: string, kind: "start" | "done", result?: string) =>
    request<Mark>("POST", "/marks", { assignment_id, kind, result }),
  createStream: (title: string) => request<Stream>("POST", "/streams", { title }),
  leaderboard: (id: string) =>
    request<Attempt[]>("GET", `/missions/${id}/leaderboard`),
  mission: (slug: string) => request("GET", `/m/${slug}`),
  streamStatus: (id: string) => request("GET", `/streams/${id}/status`),
  upload: (file: File, marks: unknown[]) =>
    request("POST", "/uploads", { file, marks }),
  downloadClip: (id: string) => `${base()}/clips/${id}/download`,
  results: () => request<Results>("GET", "/results"),
  history: () => request<HistoryEntry[]>("GET", "/history"),
  settings: () => request<Settings>("GET", "/settings"),
  recordMetric: (clip_id: string, views: number, avg_view_percentage: number) =>
    request("POST", "/metrics", { clip_id, views, avg_view_percentage }),
  deleteAccount: () => request("DELETE", "/account"),
  adminTemplates: () => request("GET", "/admin/templates"),
  adminUsers: () => request("GET", "/admin/users"),
  adminJobs: () => request("GET", "/admin/jobs"),
  retryJob: (id: string) => request("POST", `/admin/jobs/${id}/retry`),
  creator: (id: string) => request("GET", `/creators/${id}`),
};
