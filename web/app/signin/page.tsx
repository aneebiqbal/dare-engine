import Link from "next/link";
import { Page } from "@/components/page";
import { Badge, Button, Card, Eyebrow } from "@/components/ui";

export const dynamic = "force-dynamic";

export default function SignIn() {
  return (
    <Page eyebrow="Sign in" title="Sign in with Google">
      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <div className="flex flex-col gap-4">
            <Eyebrow>Google sign-in</Eyebrow>
            <p className="text-sm leading-relaxed text-muted">
              Clipdesk uses Google sign-in and the same consent screen connects your
              YouTube channel. No passwords are stored.
            </p>
            <Button data-testid="google-signin" disabled>
              Continue with Google
            </Button>
            <p className="text-xs text-danger">
              Needs a Google OAuth client. Blocked by Gate 0.
            </p>
          </div>
        </Card>
        <Card>
          <div className="flex flex-col gap-4">
            <Eyebrow>Before accounts exist</Eyebrow>
            <p className="text-sm leading-relaxed text-muted">
              Accounts arrive with M5. Until then the app runs as a seeded developer
              creator.
            </p>
            <Link href="/">
              <Button variant="outline">Continue as dev creator</Button>
            </Link>
          </div>
        </Card>
      </div>
    </Page>
  );
}
