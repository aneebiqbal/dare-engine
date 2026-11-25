import { Suspense } from "react";

import { AppPage } from "@/components/app-page";
import { ExportPackage } from "@/components/export-package";
import { PageState } from "@/components/ui";
import { api, type Clip } from "@/lib/api";
import { requireUser } from "@/lib/server";
import { notFound } from "next/navigation";

export const dynamic = "force-dynamic";

async function ExportData({ id }: { id: string }) {
  let clip: Clip;
  try {
    clip = await api.clip(id);
  } catch {
    notFound();
  }
  return <ExportPackage clip={clip} />;
}

export default async function ExportPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const user = await requireUser();
  return (
    <AppPage user={user} eyebrow="Export" title="Export package" header={false}>
      <Suspense fallback={<PageState loading />}>
        <ExportData id={id} />
      </Suspense>
    </AppPage>
  );
}
