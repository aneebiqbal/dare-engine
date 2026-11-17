import { Remote } from "@/components/remote";
import { api, type Today as TodayResponse } from "@/lib/api";
import { requireUser } from "@/lib/server";

export const dynamic = "force-dynamic";

export default async function RemotePage() {
  await requireUser();
  let mission: TodayResponse["daily"];
  try {
    const data = await api.today();
    mission = data.daily ?? data.picks?.[0] ?? null;
  } catch {
    mission = null;
  }
  if (!mission) {
    return (
      <main className="flex min-h-[100dvh] items-center justify-center p-6 text-center text-muted">
        No mission today yet.
      </main>
    );
  }
  return <Remote mission={mission} />;
}
