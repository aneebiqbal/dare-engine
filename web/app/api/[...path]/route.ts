import { NextRequest, NextResponse } from "next/server";

import { clearApiCache } from "@/lib/api";

const API = process.env.API_URL ?? "http://api:8000";

/** Same-origin proxy so the session cookie stays on the web origin. */
async function proxy(req: NextRequest, method: string) {
  const path = req.nextUrl.pathname.replace(/^\/api/, "") + req.nextUrl.search;
  if (method !== "GET" && method !== "HEAD") clearApiCache();
  const headers: Record<string, string> = {};
  const cookie = req.headers.get("cookie");
  if (cookie) headers["Cookie"] = cookie;
  const contentType = req.headers.get("content-type");
  if (contentType) headers["Content-Type"] = contentType;
  const csrf = req.headers.get("x-csrf-token");
  if (csrf) headers["X-CSRF-Token"] = csrf;

  const body = method === "GET" || method === "HEAD" ? undefined : await req.arrayBuffer();
  const res = await fetch(`${API}${path}`, { method, headers, body, cache: "no-store" });

  const out = new Headers();
  const ct = res.headers.get("content-type");
  if (ct) out.set("Content-Type", ct);
  for (const c of res.headers.getSetCookie?.() ?? []) out.append("Set-Cookie", c);

  return new NextResponse(await res.arrayBuffer(), { status: res.status, headers: out });
}

export const GET = (r: NextRequest) => proxy(r, "GET");
export const POST = (r: NextRequest) => proxy(r, "POST");
export const PATCH = (r: NextRequest) => proxy(r, "PATCH");
export const PUT = (r: NextRequest) => proxy(r, "PUT");
export const DELETE = (r: NextRequest) => proxy(r, "DELETE");
