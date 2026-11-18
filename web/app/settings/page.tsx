import { AppPage } from "@/components/app-page";
import { Settings } from "@/components/settings";
import { api, type Settings as SettingsData } from "@/lib/api";
import { requireUser } from "@/lib/server";

export const dynamic = "force-dynamic";

export default async function SettingsPage() {
  const user = await requireUser();
  let settings: SettingsData | null = null;
  let loadError = false;
  try {
    settings = await api.settings();
  } catch {
    loadError = true;
  }
  return (
    <AppPage user={user} eyebrow="Settings" title="Account settings">
      <Settings user={user} initial={settings} loadError={loadError} />
    </AppPage>
  );
}
