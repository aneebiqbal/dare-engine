import { AppPage } from "@/components/app-page";
import { AdminInvites } from "@/components/admin";
import { requireAdmin } from "@/lib/server";

export const dynamic = "force-dynamic";

export default async function AdminInvitesPage() {
  const user = await requireAdmin();
  return (
    <AppPage user={user} eyebrow="Admin" title="Invites" header={false}>
      <AdminInvites />
    </AppPage>
  );
}
