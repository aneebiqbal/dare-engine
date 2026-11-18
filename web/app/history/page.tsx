import { AppPage } from "@/components/app-page";
import { History } from "@/components/history";
import { api, type HistoryEntry } from "@/lib/api";
import { requireUser } from "@/lib/server";

export const dynamic = "force-dynamic";

export default async function HistoryPage() {
  const user = await requireUser();
  let initial: HistoryEntry[] = [];
  try {
    initial = (await api.history("?page_size=100")).items;
  } catch {
    initial = [];
  }
  return (
    <AppPage user={user} eyebrow="History" title="Mission history">
      <History initial={initial} />
    </AppPage>
  );
}
