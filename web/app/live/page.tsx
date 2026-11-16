import { Page } from "@/components/page";
import { Live } from "@/components/live";
import { api, type Stream } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function LivePage() {
  let initial: Stream | null = null;
  try {
    initial = await api.createStream("Launch day stream");
  } catch {
    initial = null;
  }
  return (
    <Page eyebrow="Go Live" title="Your stream address">
      <Live initial={initial} />
    </Page>
  );
}
