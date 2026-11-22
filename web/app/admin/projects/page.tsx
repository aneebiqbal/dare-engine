import { AppPage } from "@/components/app-page";
import { Projects } from "@/components/projects";
import { requireAdmin } from "@/lib/server";

export const dynamic = "force-dynamic";

export default async function AdminProjectsPage() {
  const user = await requireAdmin();
  return (
    <AppPage user={user} eyebrow="Admin" title="Projects">
      <Projects />
    </AppPage>
  );
}
