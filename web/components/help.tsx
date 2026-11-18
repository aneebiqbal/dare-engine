"use client";

import { useEffect, useState } from "react";
import { api, type HelpAnswer } from "@/lib/api";
import { Badge, Button, Card, Field, Input, Notice, PageState } from "@/components/ui";
import { replayTour } from "./tour";

function Guide({ text }: { text: string }) {
  const blocks = text.split(/\n{2,}/).filter(Boolean);
  return (
    <div className="flex flex-col gap-4">
      {blocks.map((block, i) => {
        const lines = block.split("\n");
        const first = lines[0]?.trim() ?? "";
        if (first.startsWith("## ")) {
          return (
            <h2 key={i} className="text-base font-semibold tracking-tight">
              {first.slice(3)}
            </h2>
          );
        }
        if (first.startsWith("# ")) {
          return (
            <h1 key={i} className="text-xl font-semibold tracking-tight">
              {first.slice(2)}
            </h1>
          );
        }
        if (lines.every((l) => l.trim() === "" || l.trim().startsWith("- "))) {
          return (
            <ul key={i} className="list-disc pl-5 text-sm leading-relaxed text-muted">
              {lines.filter(Boolean).map((l, j) => (
                <li key={j}>{l.trim().slice(2)}</li>
              ))}
            </ul>
          );
        }
        return (
          <p key={i} className="text-sm leading-relaxed text-muted">
            {lines.join(" ")}
          </p>
        );
      })}
    </div>
  );
}

export function Help({ role = "creator" }: { role?: string }) {
  const [guide, setGuide] = useState<string | null>(null);
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<HelpAnswer | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .helpGuide()
      .then((r) => setGuide(r.guide))
      .catch((e) => setError(e instanceof Error ? e.message : "Could not load the guide"));
  }, []);

  async function ask() {
    if (!question.trim()) return;
    setLoading(true);
    setError(null);
    try {
      setAnswer(await api.help(question));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not answer");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <Card>
        <div className="flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <Badge tone="accent">Ask the guide</Badge>
            <Button variant="ghost" size="sm" data-testid="help-replay-tour" onClick={() => replayTour(role)}>
              Replay tour
            </Button>
          </div>
          <Field label="How do I…">
            <Input
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="e.g. How do I upload a recording?"
              onKeyDown={(e) => e.key === "Enter" && void ask()}
            />
          </Field>
          <Button onClick={ask} disabled={loading}>
            {loading ? "Asking…" : "Ask"}
          </Button>
          {answer && (
            <div className="flex flex-col gap-2">
              <p className="text-sm leading-relaxed">{answer.answer}</p>
              {answer.fallback && <Notice tone="warn">{answer.notice}</Notice>}
            </div>
          )}
          {error && <Notice tone="warn">{error}</Notice>}
        </div>
      </Card>

      <Card>
        <div className="flex flex-col gap-3">
          <h2 className="text-base font-medium">Guide</h2>
          <PageState
            loading={!guide && !error}
            error={error}
            empty={false}
            emptyTitle="No guide"
            emptyBody="The guide could not be loaded."
          >
            <Guide text={guide ?? ""} />
          </PageState>
        </div>
      </Card>
    </div>
  );
}
