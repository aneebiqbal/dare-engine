import { Suspense } from "react";

import { AppPage } from "@/components/app-page";
import { ClipReview } from "@/components/clip-review";
import { PageState } from "@/components/ui";
import { api, type Clip } from "@/lib/api";
import { requireUser } from "@/lib/server";
import { notFound } from "next/navigation";

export const dynamic = "force-dynamic";

async function ClipData({ id }: { id: string }) {
  let clip: Clip;
  try {
    clip = await api.clip(id);
  } catch {
    notFound();
  }
  return <ClipReview clip={clip} />;
}

export default async function ClipPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const user = await requireUser();
  return (
    <AppPage user={user} eyebrow="Review" title="Clip review">
      <Suspense fallback={<PageState loading />}>
        <ClipData id={id} />
      </Suspense>
    </AppPage>
  );
}
