import { AppPage } from "@/components/app-page";
import { AdminAudit } from "@/components/admin";
import { requireAdmin } from "@/lib/server";

export const dynamic = "force-dynamic";

export default async function AdminAuditPage() {
  const user = await requireAdmin();
  return (
    <AppPage user={user} eyebrow="Admin" title="Audit log" header={false}>
      <AdminAudit />
    </AppPage>
  );
}
