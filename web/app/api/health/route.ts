import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export async function GET() {
  const api = process.env.API_URL ?? "http://api:8000";
  try {
    const res = await fetch(`${api}/healthz/ready`, { cache: "no-store" });
    const body = await res.json().catch(() => null);
    return NextResponse.json(
      { web: "ok", api: body ?? "unreachable" },
      { status: res.ok ? 200 : 502 },
    );
  } catch {
    return NextResponse.json({ web: "ok", api: "unreachable" }, { status: 502 });
  }
}
