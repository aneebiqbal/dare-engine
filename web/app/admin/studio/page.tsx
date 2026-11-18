import { AppPage } from "@/components/app-page";
import { Studio } from "@/components/studio";
import { requireAdmin } from "@/lib/server";

export const dynamic = "force-dynamic";

export default async function AdminStudioPage() {
  const user = await requireAdmin();
  return (
    <AppPage user={user} eyebrow="Admin" title="Clip studio">
      <Studio />
    </AppPage>
  );
}
