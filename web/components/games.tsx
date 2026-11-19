"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import {
  api,
  type Game,
  type GameProfile,
  type GameSearchEntry,
  type PoolEntry,
  type ResearchRun,
  type User,
} from "@/lib/api";
import {
  Badge,
  Button,
  Card,
  Dialog,
  Field,
  Input,
  Notice,
  PageState,
  Select,
  Stat,
  Table,
  Tabs,
  Td,
  Tr,
  useToast,
} from "@/components/ui";

export function Sources({ sources }: { sources?: PoolEntry["sources"] }) {
  if (!sources || sources.length === 0) {
    return <p className="text-xs text-danger">No source — not shown to gamers.</p>;
  }
  return (
    <ul className="flex flex-col gap-1">
      {sources.map((s) => (
        <li key={s.url} className="truncate text-xs text-muted">
          <Badge tone="muted">{s.kind}</Badge>{" "}
          <a
            href={s.url}
            target="_blank"
            rel="noreferrer"
            className="text-accent hover:underline"
          >
            {s.title}
          </a>
        </li>
      ))}
    </ul>
  );
}

function ResearchNow({ id, onDone }: { id: string; onDone: () => void }) {
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const toast = useToast();

  async function run() {
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const res = await api.adminRunResearch(id);
      setResult(
        `${res.ideas} sourced idea(s) from ${Object.entries(res.sources)
          .map(([k, n]) => `${n} ${k}`)
          .join(", ") || "no sources"}${res.fallback ? " (sample feed)" : ""}`,
      );
      toast("Research complete", "success");
      onDone();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Research failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-col gap-2">
      <Button size="sm" variant="outline" onClick={run} disabled={busy}>
        {busy ? "Researching…" : "Research now"}
      </Button>
      {result && <Notice tone="info">{result}</Notice>}
      {error && <Notice tone="warn">{error}</Notice>}
    </div>
  );
}

export function AdminGames() {
  const [items, setItems] = useState<Game[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [addOpen, setAddOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<GameSearchEntry[]>([]);
  const [searching, setSearching] = useState(false);
  const toast = useToast();

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.adminGames("?page_size=100");
      setItems(res.items);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function search() {
    if (!query.trim()) return;
    setSearching(true);
    try {
      const res = await api.adminGameSearch(query.trim());
      setResults(res.results);
    } catch (e) {
      toast(e instanceof Error ? e.message : "Search failed", "danger");
    } finally {
      setSearching(false);
    }
  }

  async function add(game: GameSearchEntry) {
    try {
      await api.adminCreateGame({
        slug: game.slug,
        name: game.name,
        external_id: game.external_id,
        genre: game.genre,
        release_date: game.release_date,
        art_url: game.art_url,
      });
      setAddOpen(false);
      setQuery("");
      setResults([]);
      await load();
      toast("Game added", "success");
    } catch (e) {
      toast(e instanceof Error ? e.message : "Could not add game", "danger");
    }
  }

  async function toggle(game: Game) {
    try {
      await api.adminUpdateGame(game.id, { enabled: !game.enabled });
      await load();
    } catch (e) {
      toast(e instanceof Error ? e.message : "Could not update", "danger");
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Button onClick={() => setAddOpen(true)}>Add game</Button>
        <span className="text-xs text-muted">Research runs daily per enabled game.</span>
      </div>

      <PageState
        loading={loading}
        error={error}
        empty={items.length === 0}
        emptyTitle="No games yet"
        emptyBody="Add a game to start daily research."
      >
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {items.map((game) => (
            <Card key={game.id} className={game.enabled ? "" : "opacity-60"}>
              <div className="flex h-full flex-col gap-3">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <Link href={`/admin/games/${game.id}`} className="block truncate text-base font-medium hover:underline">
                      {game.name}
                    </Link>
                    <p className="text-xs text-muted">
                      {game.genre ?? "—"} · {game.release_date?.slice(0, 4) ?? "—"}
                    </p>
                  </div>
                  <Badge tone={game.enabled ? "success" : "muted"}>
                    {game.enabled ? "enabled" : "off"}
                  </Badge>
                </div>
                <div className="grid grid-cols-3 gap-2 text-center">
                  <Stat label="Ideas" value={game.candidates ?? 0} />
                  <Stat label="Approved" value={game.approved ?? 0} />
                  <Stat label="Gamers" value={game.gamers ?? 0} />
                </div>
                <div className="mt-auto flex flex-wrap gap-2 pt-2">
                  <ResearchNow id={game.id} onDone={load} />
                  <Button size="sm" variant="outline" onClick={() => toggle(game)}>
                    {game.enabled ? "Disable" : "Enable"}
                  </Button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      </PageState>

      <Dialog open={addOpen} onClose={() => setAddOpen(false)} title="Add a game">
        <div className="flex flex-col gap-4">
          <Field label="Search RAWG">
            <div className="flex gap-2">
              <Input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Grand Theft Auto V"
                onKeyDown={(e) => e.key === "Enter" && void search()}
              />
              <Button onClick={search} disabled={searching || !query.trim()}>
                {searching ? "…" : "Search"}
              </Button>
            </div>
          </Field>
          {results.length === 0 ? (
            <p className="text-sm text-muted">No results. Type a game name and search.</p>
          ) : (
            <div className="flex flex-col gap-2">
              {results.map((r) => (
                <div key={r.slug} className="flex items-center justify-between gap-3 text-sm">
                  <span className="min-w-0 truncate">
                    {r.name}
                    <span className="text-muted"> · {r.genre ?? "—"}</span>
                  </span>
                  <Button size="sm" variant="outline" onClick={() => add(r)}>
                    Add
                  </Button>
                </div>
              ))}
            </div>
          )}
        </div>
      </Dialog>
    </div>
  );
}

function AssignDialog({
  entry,
  onClose,
  onAssigned,
}: {
  entry: PoolEntry | null;
  onClose: () => void;
  onAssigned: () => void;
}) {
  const [users, setUsers] = useState<User[]>([]);
  const [assignee, setAssignee] = useState("");
  const [busy, setBusy] = useState(false);
  const toast = useToast();

  useEffect(() => {
    if (!entry) return;
    setAssignee("");
    api
      .adminUsers("?page_size=100")
      .then((res) => setUsers(res.items.filter((u) => u.role !== "admin")))
      .catch(() => setUsers([]));
  }, [entry]);

  async function assign() {
    if (!entry || !assignee) return;
    setBusy(true);
    try {
      await api.assign(entry.id, assignee);
      toast("Idea assigned", "success");
      onAssigned();
      onClose();
    } catch (e) {
      toast(e instanceof Error ? e.message : "Could not assign", "danger");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Dialog open={Boolean(entry)} onClose={onClose} title={`Assign ${entry?.id ?? ""}`}>
      <div className="flex flex-col gap-4">
        <Select aria-label="Gamer" value={assignee} onChange={(e) => setAssignee(e.target.value)}>
          <option value="">Choose a gamer…</option>
          {users.map((u) => (
            <option key={u.id} value={u.id}>
              {u.display_name ?? u.email ?? u.id}
            </option>
          ))}
        </Select>
        <div className="flex justify-end gap-3">
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={assign} disabled={!assignee || busy}>
            Assign idea
          </Button>
        </div>
      </div>
    </Dialog>
  );
}

export function AdminGameProfile({ gameId }: { gameId: string }) {
  const [profile, setProfile] = useState<GameProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState("candidates");
  const [assignFor, setAssignFor] = useState<PoolEntry | null>(null);
  const toast = useToast();

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setProfile(await api.adminGame(gameId));
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }, [gameId]);

  useEffect(() => {
    void load();
  }, [load]);

  async function approve(id: string) {
    try {
      await api.approve(id);
      await load();
      toast("Idea approved", "success");
    } catch (e) {
      toast(e instanceof Error ? e.message : "Could not approve", "danger");
    }
  }

  async function reject(id: string) {
    try {
      await api.reject(id);
      await load();
      toast("Idea rejected", "success");
    } catch (e) {
      toast(e instanceof Error ? e.message : "Could not reject", "danger");
    }
  }

  if (loading) return <PageState loading />;
  if (error) return <PageState loading={false} error={error} empty={false} />;
  if (!profile) return null;

  const { game, candidates, approved, assigned, runs } = profile;

  return (
    <div className="flex flex-col gap-6">
      <Card>
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="flex min-w-0 items-center gap-4">
            {game.art_url ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={game.art_url} alt="" className="h-20 w-14 rounded-md object-cover" />
            ) : (
              <div className="flex h-20 w-14 items-center justify-center rounded-md bg-surface text-xs text-muted">
                {game.name.slice(0, 2).toUpperCase()}
              </div>
            )}
            <div className="min-w-0">
              <h2 className="truncate text-2xl font-semibold tracking-tight">{game.name}</h2>
              <p className="text-sm text-muted">
                {game.genre ?? "—"} · released {game.release_date ?? "—"} · {game.source}
                {game.external_id ? ` #${game.external_id}` : ""}
              </p>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <Badge tone={game.enabled ? "success" : "muted"}>{game.enabled ? "enabled" : "off"}</Badge>
            <ResearchNow id={game.id} onDone={load} />
          </div>
        </div>
      </Card>

      <Tabs
        tabs={[
          { id: "candidates", label: `Candidates (${candidates.length})` },
          { id: "approved", label: `Approved (${approved.length})` },
          { id: "assigned", label: `Assigned (${assigned.length})` },
          { id: "runs", label: `Research runs (${runs.length})` },
        ]}
        active={tab}
        onChange={setTab}
      />

      {tab === "candidates" && (
        <PageState
          loading={false}
          error={null}
          empty={candidates.length === 0}
          emptyTitle="No candidates"
          emptyBody="Run research to fill this game's queue."
        >
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {candidates.map((entry) => (
              <Card key={entry.id}>
                <div className="flex h-full flex-col gap-3">
                  <div className="flex items-center justify-between">
                    <Badge tone="accent">{entry.id}</Badge>
                    <img
                      src={api.cardImageUrl(entry.id)}
                      alt={`Card ${entry.id}`}
                      className="h-16 w-9 rounded-sm object-cover ring-surface"
                    />
                  </div>
                  <h3 className="text-base font-medium leading-snug">{entry.card?.question}</h3>
                  <p className="text-sm text-muted">{entry.card?.hook_text}</p>
                  <Sources sources={entry.sources} />
                  <div className="mt-auto flex flex-wrap gap-2 pt-2">
                    <Button size="sm" onClick={() => approve(entry.id)}>Approve</Button>
                    <Button size="sm" variant="outline" onClick={() => setAssignFor(entry)}>Assign</Button>
                    <Button size="sm" variant="danger" onClick={() => reject(entry.id)}>Reject</Button>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        </PageState>
      )}

      {tab === "approved" && (
        <PageState
          loading={false}
          error={null}
          empty={approved.length === 0}
          emptyTitle="Nothing approved yet"
          emptyBody="Approve a candidate to make it available to assign."
        >
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {approved.map((entry) => (
              <Card key={entry.id}>
                <div className="flex h-full flex-col gap-3">
                  <div className="flex items-center justify-between">
                    <Badge tone="success">{entry.id}</Badge>
                    <img
                      src={api.cardImageUrl(entry.id)}
                      alt={`Card ${entry.id}`}
                      className="h-16 w-9 rounded-sm object-cover ring-surface"
                    />
                  </div>
                  <h3 className="text-base font-medium leading-snug">{entry.card?.question}</h3>
                  <Sources sources={entry.sources} />
                  <div className="mt-auto flex gap-2 pt-2">
                    <Button size="sm" variant="outline" onClick={() => setAssignFor(entry)}>Assign</Button>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        </PageState>
      )}

      {tab === "assigned" && (
        <PageState
          loading={false}
          error={null}
          empty={assigned.length === 0}
          emptyTitle="No assignments"
          emptyBody="Assign an approved idea to a gamer."
        >
          <Table caption="Assigned ideas" head={["Gamer", "Idea", "State", "Date"]}>
            {assigned.map((a) => (
              <Tr key={a.assignment_id}>
                <Td>{a.display_name}</Td>
                <Td>{a.mission_id}</Td>
                <Td><Badge tone="muted">{a.state}</Badge></Td>
                <Td>{a.date}</Td>
              </Tr>
            ))}
          </Table>
        </PageState>
      )}

      {tab === "runs" && (
        <PageState
          loading={false}
          error={null}
          empty={runs.length === 0}
          emptyTitle="No research runs"
          emptyBody="Run research to see sources and ideas here."
        >
          <Table caption="Research runs" head={["When", "Status", "Sources", "Ideas", "Fallback", "Error"]}>
            {runs.map((r: ResearchRun) => (
              <Tr key={r.id}>
                <Td>{r.created_at.slice(0, 19).replace("T", " ")}</Td>
                <Td><Badge tone={r.status === "done" ? "success" : r.status === "failed" ? "danger" : "muted"}>{r.status}</Badge></Td>
                <Td>{Object.entries(r.source_counts).map(([k, n]) => `${n} ${k}`).join(", ") || "—"}</Td>
                <Td>{r.ideas_count}</Td>
                <Td>{r.fallback ? <Badge tone="muted">sample</Badge> : <Badge tone="success">live</Badge>}</Td>
                <Td className="max-w-[20rem] truncate" title={r.error ?? ""}>{r.error ?? "—"}</Td>
              </Tr>
            ))}
          </Table>
        </PageState>
      )}

      <AssignDialog entry={assignFor} onClose={() => setAssignFor(null)} onAssigned={load} />
    </div>
  );
}
