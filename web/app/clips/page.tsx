import { Suspense } from "react";

import { AppPage } from "@/components/app-page";
import { Clips } from "@/components/clips";
import { PageState } from "@/components/ui";
import { api } from "@/lib/api";
import { requireUser } from "@/lib/server";

export const dynamic = "force-dynamic";

async function ClipsData() {
  const initial = (await api.clips("?page_size=50").catch(() => null))?.items ?? [];
  return <Clips initial={initial} />;
}

export default async function ClipsPage() {
  const user = await requireUser();
  return (
    <AppPage user={user} eyebrow="Clips" title="Your Shorts">
      <Suspense fallback={<PageState loading />}>
        <ClipsData />
      </Suspense>
    </AppPage>
  );
}
