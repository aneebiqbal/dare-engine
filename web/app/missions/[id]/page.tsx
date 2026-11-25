import { Suspense } from "react";

import { AppPage } from "@/components/app-page";
import { MissionEditor } from "@/components/mission-editor";
import { PageState } from "@/components/ui";
import { api, type PoolEntry } from "@/lib/api";
import { requireUser } from "@/lib/server";
import { notFound } from "next/navigation";

export const dynamic = "force-dynamic";

async function MissionData({ id }: { id: string }) {
  let initial: PoolEntry | null = null;
  try {
    initial = await api.mission(id);
  } catch {
    notFound();
  }
  return <MissionEditor initial={initial} />;
}

export default async function MissionPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const user = await requireUser();
  return (
    <AppPage user={user} eyebrow={`Mission ${id}`} title="Dare editor" header={false}>
      <Suspense fallback={<PageState loading />}>
        <MissionData id={id} />
      </Suspense>
    </AppPage>
  );
}
