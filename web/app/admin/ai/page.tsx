import { AppPage } from "@/components/app-page";
import { AdminAi } from "@/components/admin";
import { requireAdmin } from "@/lib/server";

export const dynamic = "force-dynamic";

export default async function AdminAiPage() {
  const user = await requireAdmin();
  return (
    <AppPage user={user} eyebrow="Admin" title="AI usage" header={false}>
      <AdminAi />
    </AppPage>
  );
}
