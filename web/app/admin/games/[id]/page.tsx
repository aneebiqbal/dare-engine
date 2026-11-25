import { AppPage } from "@/components/app-page";
import { AdminGameProfile } from "@/components/games";
import { requireAdmin } from "@/lib/server";

export const dynamic = "force-dynamic";

export default async function AdminGameProfilePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const user = await requireAdmin();
  return (
    <AppPage user={user} eyebrow="Admin · Games" title="Game profile" header={false}>
      <AdminGameProfile gameId={id} />
    </AppPage>
  );
}
