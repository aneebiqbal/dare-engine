import { ClipReview } from "@/components/clip-review";
import { Page } from "@/components/page";
import { api } from "@/lib/api";
import { notFound } from "next/navigation";

export const dynamic = "force-dynamic";

export default async function ClipPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const clips = await api.clips();
  const clip = clips.find((c) => c.id === id);
  if (!clip) notFound();
  return (
    <Page eyebrow="Review" title={clip.title ?? "Untitled"}>
      <ClipReview clip={clip} />
    </Page>
  );
}
