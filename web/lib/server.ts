import { redirect } from "next/navigation";
import { api, type Me } from "./api";

export async function getMe(): Promise<Me | null> {
  try {
    return (await api.me()).user;
  } catch {
    return null;
  }
}

export async function requireUser(): Promise<Me> {
  const me = await getMe();
  if (!me) redirect("/signin");
  return me;
}

export async function requireAdmin(): Promise<Me> {
  const me = await requireUser();
  if (me.role !== "admin") redirect("/");
  return me;
}
