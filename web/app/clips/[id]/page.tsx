import { AppPage } from "@/components/app-page";
import { ClipReview } from "@/components/clip-review";
import { api, type Clip } from "@/lib/api";
import { requireUser } from "@/lib/server";
import { notFound } from "next/navigation";

export const dynamic = "force-dynamic";

export default async function ClipPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const user = await requireUser();
  let clip: Clip;
  try {
    clip = await api.clip(id);
  } catch {
    notFound();
  }
  return (
    <AppPage user={user} eyebrow="Review" title={clip.title ?? "Untitled"}>
      <ClipReview clip={clip} />
    </AppPage>
  );
}
