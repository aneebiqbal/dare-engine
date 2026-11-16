import type { paths } from "./api-types";

type TodayResponse = paths["/today"]["get"]["responses"][200]["content"]["application/json"];

export type MissionCard = NonNullable<TodayResponse["daily"]>;
export type Today = TodayResponse;
export type PoolEntry =
  paths["/admin/pool"]["get"]["responses"][200]["content"]["application/json"][number];
export type Clip = paths["/clips"]["get"]["responses"][200]["content"]["application/json"][number];
export type Mark = paths["/marks"]["post"]["responses"][201]["content"]["application/json"];
export type Stream = paths["/streams"]["post"]["responses"][201]["content"]["application/json"];
export type Me = paths["/me"]["get"]["responses"][200]["content"]["application/json"];
export type Attempt =
  paths["/missions/{id}/leaderboard"]["get"]["responses"][200]["content"]["application/json"][number];
export type Results =
  paths["/results"]["get"]["responses"][200]["content"]["application/json"];
export type HistoryEntry =
  paths["/history"]["get"]["responses"][200]["content"]["application/json"][number];
export type Settings =
  paths["/settings"]["get"]["responses"][200]["content"]["application/json"];
