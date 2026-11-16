import { Page } from "@/components/page";
import { Card, Eyebrow } from "@/components/ui";

export const dynamic = "force-dynamic";

export default function Privacy() {
  return (
    <Page eyebrow="Draft" title="Privacy policy">
      <Card>
        <div className="flex flex-col gap-4">
          <Eyebrow>Draft for legal review</Eyebrow>
          <p className="text-sm leading-relaxed text-muted">
            This document is a draft. It is not legal advice and is not final.
          </p>
          <ul className="list-disc pl-5 text-sm text-muted">
            <li>We store your provider subject id, display name and channel id.</li>
            <li>We do not store email addresses or payment details.</li>
            <li>You can export or delete your data from Settings.</li>
          </ul>
        </div>
      </Card>
    </Page>
  );
}
