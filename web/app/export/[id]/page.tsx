import { AppPage } from "@/components/app-page";
import { ExportPackage } from "@/components/export-package";
import { api, type Clip } from "@/lib/api";
import { requireUser } from "@/lib/server";
import { notFound } from "next/navigation";

export const dynamic = "force-dynamic";

export default async function ExportPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const user = await requireUser();
  let clip: Clip;
  try {
    clip = await api.clip(id);
  } catch {
    notFound();
  }
  return (
    <AppPage user={user} eyebrow="Export" title="Export package">
      <ExportPackage clip={clip} />
    </AppPage>
  );
}
