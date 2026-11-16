import { Page } from "@/components/page";
import { Badge, Card, Table, Td, Tr } from "@/components/ui";
import { api, type Results } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function ResultsPage() {
  let data: Results | null = null;
  let error: string | null = null;
  try {
    data = await api.results();
  } catch (e) {
    error = e instanceof Error ? e.message : "Failed to load results";
  }

  return (
    <Page eyebrow="Results" title="Views and retention">
      {error ? (
        <Card>
          <p className="text-sm text-danger">{error}</p>
        </Card>
      ) : !data ? null : (
        <div className="grid gap-6">
          <Table head={["Clip", "Views", "Avg. view %"]}>
            {data.clips?.map((c) => (
              <Tr key={c.clip_id}>
                <Td>{c.title}</Td>
                <Td>{c.views?.toLocaleString() ?? "—"}</Td>
                <Td>{c.avg_view_percentage ?? "—"}</Td>
              </Tr>
            ))}
          </Table>
          <div className="grid gap-4 sm:grid-cols-2">
            {data.by_type?.map((t) => (
              <Card key={t.mode}>
                <div className="flex items-center justify-between">
                  <Badge tone="accent">{t.mode}</Badge>
                  <span className="text-sm text-muted">
                    {t.clips} clips · {t.views?.toLocaleString() ?? "—"} views
                  </span>
                </div>
              </Card>
            ))}
          </div>
        </div>
      )}
    </Page>
  );
}
