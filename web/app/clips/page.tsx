import { Clips } from "@/components/clips";
import { Page } from "@/components/page";
import { api } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function ClipsPage() {
  let initial: Awaited<ReturnType<typeof api.clips>> = [];
  try {
    initial = await api.clips();
  } catch {
    initial = [];
  }
  return (
    <Page eyebrow="Clips" title="Your Shorts">
      <Clips initial={initial} />
    </Page>
  );
}
