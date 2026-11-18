import { Suspense } from "react";

import { AppPage } from "@/components/app-page";
import { History } from "@/components/history";
import { PageState } from "@/components/ui";
import { api } from "@/lib/api";
import { requireUser } from "@/lib/server";

export const dynamic = "force-dynamic";

async function HistoryData() {
  const initial = (await api.history("?page_size=100").catch(() => null))?.items ?? [];
  return <History initial={initial} />;
}

export default async function HistoryPage() {
  const user = await requireUser();
  return (
    <AppPage user={user} eyebrow="History" title="Mission history">
      <Suspense fallback={<PageState loading />}>
        <HistoryData />
      </Suspense>
    </AppPage>
  );
}
