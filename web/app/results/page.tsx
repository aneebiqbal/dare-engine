import { AppPage } from "@/components/app-page";
import { Results } from "@/components/results";
import { api, type Results as ResultsData } from "@/lib/api";
import { requireUser } from "@/lib/server";

export const dynamic = "force-dynamic";

export default async function ResultsPage() {
  const user = await requireUser();
  let initial: ResultsData | null = null;
  try {
    initial = await api.results();
  } catch {
    initial = null;
  }
  return (
    <AppPage user={user} eyebrow="Results" title="Views and retention">
      <Results initial={initial} />
    </AppPage>
  );
}
