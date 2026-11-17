import { AppPage } from "@/components/app-page";
import { AdminPool } from "@/components/admin";
import { requireAdmin } from "@/lib/server";

export const dynamic = "force-dynamic";

export default async function AdminPoolPage() {
  const user = await requireAdmin();
  return (
    <AppPage user={user} eyebrow="Admin" title="Mission pool">
      <AdminPool />
    </AppPage>
  );
}
