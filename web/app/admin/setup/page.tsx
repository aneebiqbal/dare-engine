import { AppPage } from "@/components/app-page";
import { AdminSetup } from "@/components/admin";
import { requireAdmin } from "@/lib/server";

export const dynamic = "force-dynamic";

export default async function AdminSetupPage() {
  const user = await requireAdmin();
  return (
    <AppPage user={user} eyebrow="Admin" title="Setup status" header={false}>
      <AdminSetup />
    </AppPage>
  );
}
