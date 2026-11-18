"use client";

import { useState } from "react";
import { api, type Me, type Settings } from "@/lib/api";
import { Badge, Button, Card, Field, Input, Notice, PageState, Select, useToast } from "@/components/ui";

export function Settings({ user, initial, loadError }: { user: Me; initial: Settings | null; loadError?: boolean }) {
  const [settings, setSettings] = useState<Settings | null>(initial);
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const toast = useToast();

  async function savePreferences() {
    if (!settings) return;
    setBusy(true);
    try {
      await api.updateSettings({
        caption_style: settings.caption_style,
        layout_preference: settings.layout_preference,
        voice_over_default: settings.voice_over_default,
        voice: settings.voice,
      });
      toast("Preferences saved", "success");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save");
    } finally {
      setBusy(false);
    }
  }

  async function changePassword() {
    setBusy(true);
    setNotice(null);
    setError(null);
    try {
      await api.changePassword(current, next);
      setNotice("Password changed. Other devices signed out.");
      setCurrent("");
      setNext("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not change password");
    } finally {
      setBusy(false);
    }
  }

  async function deleteAccount() {
    if (!window.confirm("Delete your account and all clips? This cannot be undone.")) return;
    setBusy(true);
    try {
      await api.deleteAccount();
      window.location.href = "/signin";
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not delete account");
      setBusy(false);
    }
  }

  return (
    <PageState
      loading={false}
      error={loadError ? "Could not load your settings. Try again in a moment." : null}
      empty={false}
    >
      {settings && (
        <div className="grid gap-4 lg:grid-cols-2">
          <Card>
            <div className="flex flex-col gap-4">
              <Badge tone="accent">{settings.plan} plan</Badge>
              <div className="flex flex-col gap-1 text-sm">
                <span className="text-muted">Signed in as</span>
                <span className="font-medium">{user.email}</span>
                <span className="text-xs text-muted">{user.display_name}</span>
              </div>
              <Field label="Clips used" hint={`${settings.clips_used} of ${settings.clips_limit}`}>
                <Input value={String(settings.clips_used)} readOnly />
              </Field>
              <div className="flex flex-wrap gap-2">
                <a
                  href={api.exportAccountUrl()}
                  className="inline-flex items-center rounded-full px-4 py-2 text-sm font-medium text-muted ring-surface transition hover:bg-surface-2 hover:text-text"
                >
                  Export my data
                </a>
                <Button variant="danger" onClick={deleteAccount} disabled={busy}>
                  Delete account
                </Button>
              </div>
            </div>
          </Card>

          <Card>
            <div className="flex flex-col gap-4">
              <h3 className="text-base font-medium">Preferences</h3>
              <Field label="Caption style">
                <Select
                  value={settings.caption_style}
                  onChange={(e) => setSettings({ ...settings, caption_style: e.target.value })}
                >
                  <option value="word">Word highlight</option>
                  <option value="none">None</option>
                </Select>
              </Field>
              <Field label="Layout preference">
                <Select
                  value={settings.layout_preference}
                  onChange={(e) => setSettings({ ...settings, layout_preference: e.target.value })}
                >
                  <option value="rotate">Rotate</option>
                  <option value="blur_fit">Blur fit</option>
                  <option value="center_crop">Centre crop</option>
                </Select>
              </Field>
              <Field label="Default voice">
                <Input
                  value={settings.voice ?? ""}
                  onChange={(e) => setSettings({ ...settings, voice: e.target.value })}
                  placeholder="en_US-amy-medium"
                />
              </Field>
              <label className="flex items-center gap-3 text-sm">
                <input
                  type="checkbox"
                  className="h-4 w-4 accent-[var(--accent)]"
                  checked={settings.voice_over_default}
                  onChange={(e) => setSettings({ ...settings, voice_over_default: e.target.checked })}
                />
                Start new clips with voice-over on
              </label>
              <Button variant="outline" onClick={savePreferences} disabled={busy}>
                Save preferences
              </Button>
            </div>
          </Card>

          <Card>
            <div className="flex flex-col gap-4">
              <h3 className="text-base font-medium">Change password</h3>
              <Field label="Current password">
                <Input type="password" value={current} onChange={(e) => setCurrent(e.target.value)} />
              </Field>
              <Field label="New password" hint="At least 10 characters.">
                <Input type="password" value={next} onChange={(e) => setNext(e.target.value)} />
              </Field>
              {notice && <Notice>{notice}</Notice>}
              {error && <Notice tone="warn">{error}</Notice>}
              <Button onClick={changePassword} disabled={busy || !current || !next}>
                Change password
              </Button>
            </div>
          </Card>
        </div>
      )}
    </PageState>
  );
}
