import { AppPage } from "@/components/app-page";
import { AdminUsers } from "@/components/admin";
import { requireAdmin } from "@/lib/server";

export const dynamic = "force-dynamic";

export default async function AdminUsersPage() {
  const user = await requireAdmin();
  return (
    <AppPage user={user} eyebrow="Admin" title="Users" header={false}>
      <AdminUsers />
    </AppPage>
  );
}
