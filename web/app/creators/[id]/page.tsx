import { Page } from "@/components/page";
import { Badge, Card, EmptyState, Table, Td, Tr } from "@/components/ui";
import { api } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function CreatorPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  let rows: { mission_id: string; result_value: number | null; clip_id: string | null; card: { question?: string } }[] = [];
  let error: string | null = null;
  try {
    rows = (await api.creator(id)).items;
  } catch (e) {
    error = e instanceof Error ? e.message : "Failed to load";
  }

  return (
    <Page eyebrow="Creator" title="Creator profile">
      {error ? (
        <Card>
          <p className="text-sm text-danger" role="alert">{error}</p>
        </Card>
      ) : rows.length === 0 ? (
        <EmptyState
          title="No public attempts yet"
          body="Attempts appear here once the creator posts a clip."
        />
      ) : (
        <div className="grid gap-4">
          <Card>
            <div className="flex flex-col gap-2">
              <Badge tone="accent">{rows.length} attempts</Badge>
              <p className="text-sm text-muted">Ranked by result, best first.</p>
            </div>
          </Card>
          <Table caption="Creator attempts" head={["Dare", "Result"]}>
            {rows.map((r) => (
              <Tr key={`${r.mission_id}-${r.clip_id ?? ""}`}>
                <Td>{r.card?.question ?? r.mission_id}</Td>
                <Td>{r.result_value ?? "—"}</Td>
              </Tr>
            ))}
          </Table>
        </div>
      )}
    </Page>
  );
}
