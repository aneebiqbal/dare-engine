import { AppPage } from "@/components/app-page";
import { AdminModels } from "@/components/models";
import { requireAdmin } from "@/lib/server";

export const dynamic = "force-dynamic";

export default async function AdminModelsPage() {
  const user = await requireAdmin();
  return (
    <AppPage user={user} eyebrow="Admin" title="Models" header={false}>
      <AdminModels />
    </AppPage>
  );
}
