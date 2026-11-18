import { Suspense } from "react";

import { Remote } from "@/components/remote";
import { api, type Today as TodayResponse } from "@/lib/api";
import { requireUser } from "@/lib/server";

export const dynamic = "force-dynamic";

async function RemoteData() {
  let data: TodayResponse | null = null;
  try {
    data = await api.today();
  } catch {
    /* the offline/error state below */
  }
  const mission = data?.daily ?? data?.picks?.[0] ?? null;
  const next = data?.picks?.find((p) => p.id !== mission?.id) ?? null;

  if (!data) {
    return (
      <div className="flex min-h-[100dvh] items-center justify-center p-6 text-center text-danger">
        Could not load today&apos;s dare. Check your connection and try again.
      </div>
    );
  }
  if (!mission) {
    return (
      <div className="flex min-h-[100dvh] items-center justify-center p-6 text-center text-muted">
        No dare today yet. Dares appear here once the admin approves them.
      </div>
    );
  }
  return <Remote mission={mission} next={next} />;
}

export default async function RemotePage() {
  await requireUser();
  return (
    <Suspense
      fallback={
        <div className="flex min-h-[100dvh] items-center justify-center p-6 text-center text-muted">
          Loading today&apos;s dare…
        </div>
      }
    >
      <RemoteData />
    </Suspense>
  );
}
