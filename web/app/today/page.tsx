import { AppPage } from "@/components/app-page";
import { Today } from "@/components/today";
import { api, type Today as TodayResponse } from "@/lib/api";
import { requireUser } from "@/lib/server";

export const dynamic = "force-dynamic";

export default async function TodayPage() {
  const user = await requireUser();
  let initial: TodayResponse | null = null;
  try {
    initial = await api.today();
  } catch {
    initial = null;
  }
  return (
    <AppPage user={user} eyebrow="Today" title="Play today's mission">
      <Today initial={initial} />
    </AppPage>
  );
}
