import { Page } from "@/components/page";
import { Today } from "@/components/today";
import { api, type Today as TodayResponse } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function Home() {
  let initial: TodayResponse = { date: "", daily: null, picks: [], accepted: {} };
  try {
    initial = await api.today();
  } catch {
    /* Today shows the error state */
  }
  return (
    <Page eyebrow="Today" title="Play today's mission">
      <Today initial={initial} />
    </Page>
  );
}
