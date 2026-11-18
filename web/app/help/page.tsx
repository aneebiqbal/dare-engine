import { AppPage } from "@/components/app-page";
import { Help } from "@/components/help";
import { requireUser } from "@/lib/server";

export const dynamic = "force-dynamic";

export default async function HelpPage() {
  const user = await requireUser();
  return (
    <AppPage user={user} eyebrow="Help" title="Guide and tours">
      <Help role={user.role} />
    </AppPage>
  );
}
