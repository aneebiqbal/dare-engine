import { Page } from "@/components/page";
import { Reset } from "@/components/reset";

export const dynamic = "force-dynamic";

export default function ResetPage() {
  return (
    <Page eyebrow="Reset password" title="Set a new password">
      <Reset />
    </Page>
  );
}
