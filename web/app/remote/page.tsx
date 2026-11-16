import { Remote } from "@/components/remote";
import { api, type Today } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function RemotePage() {
  const data: Today = await api.today();
  const mission = data.daily ?? data.picks?.[0];
  if (!mission) {
    return (
      <main className="flex min-h-[100dvh] items-center justify-center p-6 text-center text-muted">
        No mission today yet.
      </main>
    );
  }
  return <Remote mission={mission} />;
}
