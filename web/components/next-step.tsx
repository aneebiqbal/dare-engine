import Link from "next/link";
import { Icon } from "./icons";

/**
 * The persistent "what's next" affordance. Each page passes the step that
 * follows from its real state, so the journey never dead-ends.
 */
export function NextStep({
  href,
  title,
  body,
  testId = "next-step",
}: {
  href: string;
  title: string;
  body: string;
  testId?: string;
}) {
  return (
    <Link
      href={href}
      data-testid={testId}
      className="group flex items-center justify-between gap-4 rounded-lg bg-surface p-1.5 ring-surface transition duration-300 ease-out hover:bg-surface-2"
    >
      <div className="flex flex-col gap-1 rounded-[calc(2rem-0.375rem)] bg-surface-2 px-5 py-4">
        <span className="text-[10px] uppercase tracking-[0.2em] text-muted">Up next</span>
        <span className="text-base font-semibold tracking-tight text-text">{title}</span>
        <span className="text-sm text-muted">{body}</span>
      </div>
      <span className="mr-4 grid h-9 w-9 shrink-0 place-items-center rounded-full bg-surface text-muted ring-surface transition duration-300 ease-out group-hover:translate-x-1 group-hover:text-text">
        <Icon name="arrow" size={16} />
      </span>
    </Link>
  );
}
