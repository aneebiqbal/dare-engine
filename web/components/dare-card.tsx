import Link from "next/link";
import type { ReactNode } from "react";
import { api } from "@/lib/api";
import { Badge, Card } from "./ui";
import { Thumb } from "./media";

export type DareCardData = {
  id: string;
  hook_text: string;
  question: string;
  win_condition: string;
  est_minutes: number;
  mode?: string;
};

/**
 * The dare card is the unit of the product: the same draw on Today, the
 * dashboard, the admin pool and the public mission page.
 */
export function DareCard({
  card,
  highlight = false,
  image = false,
  sources,
  href,
  children,
}: {
  card: DareCardData;
  highlight?: boolean;
  image?: boolean;
  sources?: { title: string; url: string }[];
  href?: string;
  children?: ReactNode;
}) {
  return (
    <Card className={highlight ? "signature" : ""}>
      <div className="flex h-full flex-col gap-3">
        <div className="flex items-center justify-between">
          <Badge tone={highlight ? "accent" : "muted"}>
            {highlight ? "Daily dare" : card.mode ?? card.id}
          </Badge>
          <span className="text-xs text-muted">{card.est_minutes} min</span>
        </div>
        {image && (
          <Thumb
            src={api.cardImageUrl(card.id)}
            alt={`Card for ${card.hook_text}`}
            className="aspect-[9/16] w-full rounded-md object-cover ring-surface"
          />
        )}
        <h3 className="text-2xl font-semibold leading-tight tracking-tight">{card.hook_text}</h3>
        <p className="text-sm text-muted">{card.question}</p>
        <p className="text-sm">{card.win_condition}</p>
        {sources && sources.length > 0 && (
          <ul className="flex flex-col gap-1 text-xs text-muted" data-testid="dare-sources">
            {sources.map((s) => (
              <li key={s.url} className="truncate">
                <a
                  href={s.url}
                  target="_blank"
                  rel="noreferrer"
                  className="hover:text-text hover:underline"
                >
                  {s.title}
                </a>
              </li>
            ))}
          </ul>
        )}
        {children}
        {href && (
          <Link href={href} className="mt-auto pt-2 text-sm text-text underline decoration-border underline-offset-4 hover:text-accent">
            Edit dare
          </Link>
        )}
      </div>
    </Card>
  );
}
