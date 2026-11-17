import { AppPage } from "@/components/app-page";
import { AdminJobs } from "@/components/admin";
import { requireAdmin } from "@/lib/server";

export const dynamic = "force-dynamic";

export default async function AdminJobsPage() {
  const user = await requireAdmin();
  return (
    <AppPage user={user} eyebrow="Admin" title="Job queue">
      <AdminJobs />
    </AppPage>
  );
}
