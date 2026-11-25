"use client";

import { useState } from "react";
import {
  Badge,
  Button,
  Card,
  Dialog,
  Eyebrow,
  EmptyState,
  Field,
  Input,
  Notice,
  PageState,
  Progress,
  Select,
  Skeleton,
  Stat,
  StatusDot,
  Table,
  Tabs,
  Textarea,
  Td,
  Tr,
  useToast,
} from "@/components/ui";
import { ThemeToggle } from "@/components/theme";
import { Metric, Pipeline, ProgressCard, StatusBadge, WorkQueue } from "@/components/work";

export default function Styleguide() {
  const [tab, setTab] = useState("one");
  const [open, setOpen] = useState(false);
  const toast = useToast();

  return (
    <main className="mx-auto flex min-h-[100dvh] max-w-4xl flex-col gap-12 px-6 py-12">
      <header className="flex items-center justify-between">
        <div className="flex flex-col gap-3">
          <Eyebrow>Styleguide</Eyebrow>
          <h1 className="text-4xl font-semibold tracking-tight">Clipdesk design system</h1>
        </div>
        <ThemeToggle />
      </header>

      <section className="flex flex-col gap-4">
        <h2 className="folio">Buttons</h2>
        <div className="flex flex-wrap gap-3">
          <Button>Primary</Button>
          <Button variant="outline">Outline</Button>
          <Button variant="ghost">Ghost</Button>
          <Button variant="danger">Danger</Button>
          <Button size="lg">Large</Button>
        </div>
      </section>

      <section className="flex flex-col gap-4">
        <h2 className="folio">Badges</h2>
        <div className="flex flex-wrap gap-3">
          <Badge>Mission</Badge>
          <Badge tone="accent">Daily</Badge>
          <Badge tone="success">Ready</Badge>
          <Badge tone="danger">Failed</Badge>
        </div>
      </section>

      <section className="flex flex-col gap-4">
        <h2 className="folio">Inputs</h2>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Title">
            <Input placeholder="A title" />
          </Field>
          <Field label="With error" error="Required">
            <Input aria-invalid="true" />
          </Field>
        </div>
        <Textarea rows={3} placeholder="Description" />
        <Field label="Choice">
          <Select>
            <option value="one">One</option>
            <option value="two">Two</option>
          </Select>
        </Field>
      </section>

      <section className="flex flex-col gap-4">
        <h2 className="folio">Status</h2>
        <div className="flex flex-wrap gap-6">
          <span className="flex items-center gap-2 text-sm"><StatusDot tone="success" label="Ready" /> Ready</span>
          <span className="flex items-center gap-2 text-sm"><StatusDot tone="danger" label="Failed" /> Failed</span>
          <span className="flex items-center gap-2 text-sm"><StatusDot tone="accent" label="Live" /> Live</span>
          <span className="flex items-center gap-2 text-sm"><StatusDot label="Idle" /> Idle</span>
        </div>
        <Progress value={64} label="Render progress" />
        <Notice>Rendering uses the local FFmpeg pipeline.</Notice>
      </section>

      <section className="flex flex-col gap-4">
        <h2 className="folio">Stat tile</h2>
        <div className="grid gap-4 sm:grid-cols-3">
          <Card><Stat label="Views" value="1,204" hint="last 30 days" /></Card>
          <Card><Stat label="Clips" value="12" /></Card>
          <Card><Stat label="Next step" value="Review" hint="1 ready" /></Card>
        </div>
      </section>

      <section className="flex flex-col gap-4">
        <h2 className="folio">Card</h2>
        <Card>
          <div className="flex flex-col gap-2">
            <Badge tone="accent">m_0214</Badge>
            <h3 className="text-lg font-medium">Can you outrun five stars on a bicycle?</h3>
            <p className="text-sm text-muted">Lose the wanted level without leaving the bike.</p>
          </div>
        </Card>
      </section>

      <section className="flex flex-col gap-4">
        <h2 className="folio">Tabs</h2>
        <Tabs
          tabs={[{ id: "one", label: "One" }, { id: "two", label: "Two" }]}
          active={tab}
          onChange={setTab}
        />
      </section>

      <section className="flex flex-col gap-4">
        <h2 className="folio">Table</h2>
        <Table head={["Clip", "State", "Views"]}>
          <Tr>
            <Td>5 STARS. ONE BICYCLE.</Td>
            <Td>
              <Badge tone="success">ready</Badge>
            </Td>
            <Td>1,204</Td>
          </Tr>
          <Tr>
            <Td>NO BRAKES. NO PROBLEM.</Td>
            <Td>
              <Badge>rendering</Badge>
            </Td>
            <Td>—</Td>
          </Tr>
        </Table>
      </section>

      <section className="flex flex-col gap-4">
        <h2 className="folio">States</h2>
        <PageState loading>
          <span />
        </PageState>
        <PageState error="The API could not be reached.">
          <span />
        </PageState>
        <PageState empty>
          <span />
        </PageState>
        <EmptyState title="Nothing here yet" body="This is the empty state." icon="◌" />
        <Skeleton className="h-20" />
      </section>

      <section className="flex flex-col gap-4">
        <h2 className="folio">Work kit</h2>
        <div className="flex flex-wrap gap-2">
          <StatusBadge status="running" />
          <StatusBadge status="needs" />
          <StatusBadge status="done" />
          <StatusBadge status="failed" />
          <StatusBadge status="idle" />
        </div>
        <Pipeline steps={["fetch", "write", "store"]} current={1} label="Research progress" />
        <Pipeline
          steps={["planned", "recording", "imported", "analyzing", "clips_ready", "reviewed", "exported"]}
          current={3}
          label="Project stage"
        />
        <div className="grid gap-4 sm:grid-cols-3">
          <Card>
            <Metric label="Host RAM" value="18.4 / 32 GB" hint="58% used" />
          </Card>
          <Card>
            <ProgressCard
              title="Friday stream — GTA"
              status="running"
              progress={50}
              stage="analyzing"
              meta="5 candidates"
            />
          </Card>
          <Card>
            <WorkQueue
              items={[
                { id: "1", title: "detect_moments", subtitle: "transcribe", status: "running", meta: "45%" },
                { id: "2", title: "render_clip", subtitle: "failed", status: "failed", meta: "render" },
              ]}
            />
          </Card>
        </div>
      </section>

      <section className="flex flex-col gap-4">
        <h2 className="folio">Dialog & toast</h2>
        <div className="flex gap-3">
          <Button variant="outline" onClick={() => setOpen(true)}>
            Open dialog
          </Button>
          <Button variant="outline" onClick={() => toast("Saved", "success")}>
            Show toast
          </Button>
        </div>
        <Dialog open={open} onClose={() => setOpen(false)} title="Delete clip?">
          <p className="mb-5 text-sm text-muted">This removes the clip and its files.</p>
          <div className="flex justify-end gap-3">
            <Button variant="ghost" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button variant="danger" onClick={() => setOpen(false)}>
              Delete
            </Button>
          </div>
        </Dialog>
      </section>
    </main>
  );
}
