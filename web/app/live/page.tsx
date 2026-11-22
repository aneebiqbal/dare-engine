import { AppPage } from "@/components/app-page";
import { Live } from "@/components/live";
import { requireUser } from "@/lib/server";

export const dynamic = "force-dynamic";

export default async function LivePage() {
  const user = await requireUser();
  // The stream address is issued client-side so the CSRF header is present.
  return (
    <AppPage user={user} eyebrow="Go Live" title="Your stream address" header={false}>
      <Live initial={null} />
    </AppPage>
  );
}
