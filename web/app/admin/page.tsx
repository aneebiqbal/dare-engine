import { Admin, type PoolEntry } from "@/components/admin";

export const dynamic = "force-dynamic";

export default async function AdminPage() {
  const api = process.env.API_URL ?? "http://api:8000";
  const res = await fetch(`${api}/admin/pool`, { cache: "no-store" });
  const pool: PoolEntry[] = res.ok ? await res.json() : [];
  return <Admin pool={pool} />;
}
