import { Page } from "@/components/page";
import { Badge, Card, Eyebrow } from "@/components/ui";
import { api, type Attempt, type MissionCard } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function MissionPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  let card: MissionCard | null = null;
  let attempts: Attempt[] = [];
  try {
    const data = await api.mission(slug);
    card = (data as { card?: MissionCard }).card ?? null;
    attempts = (data as { attempts?: Attempt[] }).attempts ?? [];
  } catch {
    /* fall through to the empty state */
  }

  return (
    <Page eyebrow={`Mission ${slug}`} title={card?.hook_text ?? "Mission"}>
      <div className="grid gap-4 lg:grid-cols-[1fr_2fr]">
        <Card>
          <div className="flex flex-col gap-3">
            <Badge tone="accent">{card?.mode ?? "free_roam"}</Badge>
            <p className="text-lg font-medium">{card?.question}</p>
            <p className="text-sm text-muted">{card?.setup}</p>
            <p className="text-sm text-muted">{card?.win_condition}</p>
          </div>
        </Card>
        <div className="flex flex-col gap-4">
          <Eyebrow>Attempts</Eyebrow>
          {attempts.length === 0 ? (
            <Card>
              <p className="text-sm text-muted">No attempts yet. Be the first.</p>
            </Card>
          ) : (
            <div className="grid gap-3 sm:grid-cols-2">
              {attempts.map((a) => (
                <Card key={a.rank}>
                  <div className="flex items-center justify-between">
                    <Badge tone="accent">#{a.rank}</Badge>
                    <span className="text-sm text-muted">{a.result_value}</span>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </div>
      </div>
    </Page>
  );
}
