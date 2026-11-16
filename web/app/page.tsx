import { Today, type TodayData } from "@/components/today";

export const dynamic = "force-dynamic";

export default async function Home() {
  const api = process.env.API_URL ?? "http://api:8000";
  const res = await fetch(`${api}/today`, { cache: "no-store" });
  const data: TodayData = res.ok
    ? await res.json()
    : { date: "", daily: null, picks: [], accepted: {} };
  return <Today data={data} />;
}
