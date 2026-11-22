import { AppPage } from "@/components/app-page";
import { SetupWizard } from "@/components/wizard";
import { requireAdmin } from "@/lib/server";

export const dynamic = "force-dynamic";

export default async function AdminWizardPage() {
  const user = await requireAdmin();
  return (
    <AppPage user={user} eyebrow="Admin" title="Setup wizard">
      <SetupWizard />
    </AppPage>
  );
}
