import { Suspense } from "react";

import { AppPage } from "@/components/app-page";
import { Settings } from "@/components/settings";
import { PageState } from "@/components/ui";
import { api, type Me, type Settings as SettingsData } from "@/lib/api";
import { requireUser } from "@/lib/server";

export const dynamic = "force-dynamic";

async function SettingsData({ user }: { user: Me }) {
  let settings: SettingsData | null = null;
  let loadError = false;
  try {
    settings = await api.settings();
  } catch {
    loadError = true;
  }
  return <Settings user={user} initial={settings} loadError={loadError} />;
}

export default async function SettingsPage() {
  const user = await requireUser();
  return (
    <AppPage user={user} eyebrow="Settings" title="Account settings">
      <Suspense fallback={<PageState loading />}>
        <SettingsData user={user} />
      </Suspense>
    </AppPage>
  );
}
