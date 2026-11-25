import { AppPage } from "@/components/app-page";
import { AdminOverview } from "@/components/admin";
import { requireAdmin } from "@/lib/server";

export const dynamic = "force-dynamic";

export default async function AdminPage() {
  const user = await requireAdmin();
  return (
    <AppPage user={user} eyebrow="Admin" title="Overview" header={false}>
      <AdminOverview />
    </AppPage>
  );
}
