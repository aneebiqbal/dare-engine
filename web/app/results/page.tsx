import { Suspense } from "react";

import { AppPage } from "@/components/app-page";
import { Results } from "@/components/results";
import { PageState } from "@/components/ui";
import { api } from "@/lib/api";
import { requireUser } from "@/lib/server";

export const dynamic = "force-dynamic";

async function ResultsData() {
  const initial = await api.results().catch(() => null);
  return <Results initial={initial} />;
}

export default async function ResultsPage() {
  const user = await requireUser();
  return (
    <AppPage user={user} eyebrow="Results" title="Views and retention">
      <Suspense fallback={<PageState loading />}>
        <ResultsData />
      </Suspense>
    </AppPage>
  );
}
