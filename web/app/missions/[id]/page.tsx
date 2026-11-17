import { AppPage } from "@/components/app-page";
import { MissionEditor } from "@/components/mission-editor";
import { api, type PoolEntry } from "@/lib/api";
import { requireUser } from "@/lib/server";
import { notFound } from "next/navigation";

export const dynamic = "force-dynamic";

export default async function MissionPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const user = await requireUser();
  let initial: PoolEntry | null = null;
  try {
    initial = await api.mission(id);
  } catch {
    notFound();
  }
  return (
    <AppPage user={user} eyebrow={`Mission ${id}`} title={initial.card.hook_text}>
      <MissionEditor initial={initial} />
    </AppPage>
  );
}
