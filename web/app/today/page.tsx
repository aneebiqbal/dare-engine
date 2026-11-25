import { Suspense } from "react";

import { AppPage } from "@/components/app-page";
import { Today } from "@/components/today";
import { PageState } from "@/components/ui";
import { api } from "@/lib/api";
import { requireUser } from "@/lib/server";

export const dynamic = "force-dynamic";

async function TodayData() {
  const initial = await api.today().catch(() => null);
  return <Today initial={initial} />;
}

export default async function TodayPage() {
  const user = await requireUser();
  return (
    <AppPage user={user} eyebrow="Today" title="Play today's mission" header={false}>
      <Suspense fallback={<PageState loading />}>
        <TodayData />
      </Suspense>
    </AppPage>
  );
}
