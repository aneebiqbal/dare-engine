import { AppPage } from "@/components/app-page";
import { AdminLongForm } from "@/components/longform";
import { requireAdmin } from "@/lib/server";

export const dynamic = "force-dynamic";

export default async function AdminLongFormPage() {
  const user = await requireAdmin();
  return (
    <AppPage user={user} eyebrow="Admin" title="Long-form" header={false}>
      <AdminLongForm />
    </AppPage>
  );
}
