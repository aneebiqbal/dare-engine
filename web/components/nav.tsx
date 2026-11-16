import Link from "next/link";
import { ThemeToggle } from "./theme";

const LINKS: [string, string][] = [
  ["/", "Today"],
  ["/remote", "Remote"],
  ["/clips", "Clips"],
  ["/live", "Go Live"],
  ["/results", "Results"],
  ["/settings", "Settings"],
  ["/admin", "Admin"],
  ["/welcome", "Home"],
];

export function Nav() {
  return (
    <nav className="flex flex-wrap items-center gap-1 rounded-full bg-surface p-1 ring-surface">
      {LINKS.map(([href, label]) => (
        <Link
          key={href}
          href={href}
          className="rounded-full px-3 py-1.5 text-xs text-muted transition duration-300 ease-out hover:bg-surface-2 hover:text-text"
        >
          {label}
        </Link>
      ))}
      <ThemeToggle />
    </nav>
  );
}
