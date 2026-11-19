import { AppPage } from "@/components/app-page";
import { AdminGames } from "@/components/games";
import { requireAdmin } from "@/lib/server";

export const dynamic = "force-dynamic";

export default async function AdminGamesPage() {
  const user = await requireAdmin();
  return (
    <AppPage user={user} eyebrow="Admin" title="Games">
      <AdminGames />
    </AppPage>
  );
}
