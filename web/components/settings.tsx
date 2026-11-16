"use client";

import { useState } from "react";
import { Button, Card, Field, Input, Badge, useToast } from "@/components/ui";
import type { Settings } from "@/lib/api";

export function Settings({ initial }: { initial: Settings | null }) {
  const [plan, setPlan] = useState(initial?.plan ?? "free");
  const [used, setUsed] = useState(initial?.clips_used ?? 0);
  const [limit, setLimit] = useState(initial?.clips_limit ?? 5);
  const toast = useToast();

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Card>
        <div className="flex flex-col gap-4">
          <Badge tone={plan === "paid" ? "accent" : "muted"}>{plan} plan</Badge>
          <Field label="Clips used" hint={`${used} of ${limit} this period`}>
            <Input value={String(used)} readOnly />
          </Field>
          <Button variant="outline" onClick={() => toast("Upgrade needs a payment provider", "danger")}>
            Upgrade
          </Button>
        </div>
      </Card>
      <Card>
        <div className="flex flex-col gap-4">
          <Field label="Caption style">
            <Input defaultValue={initial?.caption_style ?? "word"} />
          </Field>
          <Field label="Layout preference">
            <Input defaultValue={initial?.layout_preference ?? "rotate"} />
          </Field>
          <Button variant="outline" onClick={() => toast("Preferences saved", "success")}>
            Save preferences
          </Button>
        </div>
      </Card>
      <Card>
        <div className="flex flex-col gap-4">
          <h3 className="text-base font-medium">Data</h3>
          <div className="flex flex-wrap gap-3">
            <Button variant="outline" onClick={() => toast("Export queued", "success")}>
              Export my data
            </Button>
            <Button variant="danger" onClick={() => toast("Account deletion needs confirmation", "danger")}>
              Delete account
            </Button>
          </div>
        </div>
      </Card>
    </div>
  );
}
