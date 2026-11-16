import { Page } from "@/components/page";
import { Badge, Card, EmptyState } from "@/components/ui";

export const dynamic = "force-dynamic";

export default async function CreatorPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return (
    <Page eyebrow="Creator" title={`Creator ${id}`}>
      <div className="grid gap-4 lg:grid-cols-3">
        <Card>
          <div className="flex flex-col gap-3">
            <Badge tone="accent">Rank #12</Badge>
            <p className="text-sm text-muted">12 missions · 3 wins</p>
          </div>
        </Card>
        <div className="lg:col-span-2">
          <EmptyState
            title="No public attempts yet"
            body="Attempts appear here once the creator posts a clip."
          />
        </div>
      </div>
    </Page>
  );
}
