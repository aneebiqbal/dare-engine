"use client";

import { useEffect, useState } from "react";
import { api, type HelpAnswer } from "@/lib/api";
import { Badge, Button, Card, Field, Input, Notice, PageState, useToast } from "@/components/ui";
import { replayTour } from "./tour";

export function Help() {
  const [guide, setGuide] = useState<string | null>(null);
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<HelpAnswer | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const toast = useToast();

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
            <Button variant="ghost" size="sm" onClick={() => replayTour("creator")}>
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
          <PageState loading={!guide && !error} error={error} empty={false}>
            <pre className="whitespace-pre-wrap font-sans text-sm leading-relaxed text-muted">
              {guide}
            </pre>
          </PageState>
        </div>
      </Card>
    </div>
  );
}
