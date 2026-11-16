import { Page } from "@/components/page";
import { Badge, Button, Card, Field, Input, useToast } from "@/components/ui";
import { Settings as SettingsForm } from "@/components/settings";
import { api, type Settings } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function SettingsPage() {
  let settings: Settings | null = null;
  try {
    settings = await api.settings();
  } catch {
    settings = null;
  }
  return (
    <Page eyebrow="Settings" title="Account settings">
      <SettingsForm initial={settings} />
    </Page>
  );
}
