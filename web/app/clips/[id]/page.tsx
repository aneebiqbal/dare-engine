import { AppPage } from "@/components/app-page";
import { ClipReview } from "@/components/clip-review";
import { api, ApiError, type Clip } from "@/lib/api";
import { requireUser } from "@/lib/server";
import { notFound } from "next/navigation";

export const dynamic = "force-dynamic";

export default async function ClipPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const user = await requireUser();
  let clip: Clip | null = null;
  let loadError: string | null = null;
  try {
    clip = await api.clip(id);
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) notFound();
    loadError = e instanceof Error ? e.message : "Could not load this clip.";
  }
  if (!clip) {
    return (
      <AppPage user={user} eyebrow="Review" title="Clip">
        <div role="alert" className="rounded-lg bg-surface p-1.5 ring-surface">
          <div className="rounded-[calc(2rem-0.375rem)] bg-surface-2 px-6 py-16 text-center text-danger">
            {loadError ?? "Clip not found."}
          </div>
        </div>
      </AppPage>
    );
  }
  return (
    <AppPage user={user} eyebrow="Review" title={clip.title ?? "Untitled"}>
      <ClipReview clip={clip} />
    </AppPage>
  );
}
