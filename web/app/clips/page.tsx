import { AppPage } from "@/components/app-page";
import { Clips } from "@/components/clips";
import { api, type Clip } from "@/lib/api";
import { requireUser } from "@/lib/server";

export const dynamic = "force-dynamic";

export default async function ClipsPage() {
  const user = await requireUser();
  let initial: Clip[] = [];
  try {
    initial = (await api.clips("?page_size=50")).items;
  } catch {
    initial = [];
  }
  return (
    <AppPage user={user} eyebrow="Clips" title="Your Shorts">
      <Clips initial={initial} />
    </AppPage>
  );
}
