import { NextRequest, NextResponse } from "next/server";

const API = process.env.API_URL ?? "http://api:8000";

/** Same-origin proxy so the session cookie stays on the web origin. */
async function proxy(req: NextRequest, method: string) {
  const path = req.nextUrl.pathname.replace(/^\/api/, "") + req.nextUrl.search;
  const headers: Record<string, string> = {};
  const cookie = req.cookies.get("clipdesk_session")?.value;
  if (cookie) headers["Cookie"] = `clipdesk_session=${cookie}`;
  const contentType = req.headers.get("content-type");
  if (contentType) headers["Content-Type"] = contentType;

  const body = method === "GET" || method === "HEAD" ? undefined : await req.text();
  const res = await fetch(`${API}${path}`, { method, headers, body, cache: "no-store" });

  const out = new Headers();
  const ct = res.headers.get("content-type");
  if (ct) out.set("Content-Type", ct);
  for (const c of res.headers.getSetCookie?.() ?? []) out.append("Set-Cookie", c);

  return new NextResponse(await res.text(), { status: res.status, headers: out });
}

export const GET = (r: NextRequest) => proxy(r, "GET");
export const POST = (r: NextRequest) => proxy(r, "POST");
export const PATCH = (r: NextRequest) => proxy(r, "PATCH");
export const PUT = (r: NextRequest) => proxy(r, "PUT");
export const DELETE = (r: NextRequest) => proxy(r, "DELETE");
