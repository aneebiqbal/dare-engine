import { AppPage } from "@/components/app-page";
import { AdminTemplates } from "@/components/admin";
import { requireAdmin } from "@/lib/server";

export const dynamic = "force-dynamic";

export default async function AdminTemplatesPage() {
  const user = await requireAdmin();
  return (
    <AppPage user={user} eyebrow="Admin" title="Templates" header={false}>
      <AdminTemplates />
    </AppPage>
  );
}
