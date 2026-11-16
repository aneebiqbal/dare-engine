import { Page } from "@/components/page";
import { SignIn } from "@/components/signin";

export const dynamic = "force-dynamic";

export default function SignInPage() {
  return (
    <Page eyebrow="Sign in" title="Sign in to Clipdesk">
      <SignIn />
    </Page>
  );
}
