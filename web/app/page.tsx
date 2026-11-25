import { AppPage } from "@/components/app-page";
import { Dashboard } from "@/components/dashboard";
import { requireUser } from "@/lib/server";

export const dynamic = "force-dynamic";

export default async function Home() {
  const user = await requireUser();
  return (
    <AppPage user={user} eyebrow="Dashboard" title="Your day" header={false}>
      <Dashboard role={user.role} />
    </AppPage>
  );
}
