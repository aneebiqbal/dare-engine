import { Page } from "@/components/page";
import { SignUp } from "@/components/signup";

export const dynamic = "force-dynamic";

export default function SignUpPage() {
  return (
    <Page eyebrow="Sign up" title="Create your account">
      <SignUp />
    </Page>
  );
}
