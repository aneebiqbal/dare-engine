import { Admin } from "@/components/admin";
import { Page } from "@/components/page";
import { api, type PoolEntry } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function AdminPage() {
  let initial: PoolEntry[] = [];
  try {
    initial = await api.pool();
  } catch {
    initial = [];
  }
  return (
    <Page eyebrow="Admin" title="Mission pool">
      <Admin initial={initial} />
    </Page>
  );
}
