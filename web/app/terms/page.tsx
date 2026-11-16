import { Page } from "@/components/page";
import { Card, Eyebrow } from "@/components/ui";

export const dynamic = "force-dynamic";

export default function Terms() {
  return (
    <Page eyebrow="Draft" title="Terms of service">
      <Card>
        <div className="flex flex-col gap-4">
          <Eyebrow>Draft for legal review</Eyebrow>
          <p className="text-sm leading-relaxed text-muted">
            This document is a draft. It is not legal advice and is not final.
          </p>
          <ul className="list-disc pl-5 text-sm text-muted">
            <li>You own your gameplay and your clips.</li>
            <li>Clipdesk provides the mission cards and the rendering tools.</li>
            <li>You are responsible for what you publish.</li>
          </ul>
        </div>
      </Card>
    </Page>
  );
}
