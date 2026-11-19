import { AppPage } from "@/components/app-page";
import { AdminCalendar } from "@/components/calendar";
import { requireAdmin } from "@/lib/server";

export const dynamic = "force-dynamic";

export default async function AdminCalendarPage() {
  const user = await requireAdmin();
  return (
    <AppPage user={user} eyebrow="Admin" title="Calendar">
      <AdminCalendar />
    </AppPage>
  );
}
