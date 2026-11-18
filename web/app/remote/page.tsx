import { Remote } from "@/components/remote";
import { api, type Today as TodayResponse } from "@/lib/api";
import { requireUser } from "@/lib/server";

export const dynamic = "force-dynamic";

export default async function RemotePage() {
  await requireUser();
  let data: TodayResponse | null = null;
  let failed = false;
  try {
    data = await api.today();
  } catch {
    failed = true;
  }
  const mission = data?.daily ?? data?.picks?.[0] ?? null;
  const next = data?.picks?.find((p) => p.id !== mission?.id) ?? null;

  if (failed) {
    return (
      <main className="flex min-h-[100dvh] items-center justify-center p-6 text-center text-danger">
        Could not load today&apos;s dare. Check your connection and try again.
      </main>
    );
  }
  if (!mission) {
    return (
      <main className="flex min-h-[100dvh] items-center justify-center p-6 text-center text-muted">
        No dare today yet. Dares appear here once the admin approves them.
      </main>
    );
  }
  return <Remote mission={mission} next={next} />;
}
