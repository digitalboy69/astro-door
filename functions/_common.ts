export const SB = Deno.env.get("SUPABASE_URL")!;
export const SRK = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
export const cors = { "Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "authorization, content-type, apikey, x-client-info", "Access-Control-Allow-Methods": "GET, POST, OPTIONS" };
export const json = (o: unknown, s = 200) => new Response(JSON.stringify(o), { status: s, headers: { ...cors, "Content-Type": "application/json", "Cache-Control": "no-store" } });
export const svc = { apikey: SRK, Authorization: "Bearer " + SRK, "Content-Type": "application/json" };
export async function userFrom(req: Request) {
  const jwt = (req.headers.get("Authorization") || "").replace(/^Bearer\s+/i, "");
  if (!jwt) return null;
  const u = await fetch(SB + "/auth/v1/user", { headers: { apikey: SRK, Authorization: "Bearer " + jwt } });
  if (!u.ok) return null;
  const user = await u.json();
  return user && user.id ? user : null;
}
export async function hmacHex(secret: string, msg: string) {
  const k = await crypto.subtle.importKey("raw", new TextEncoder().encode(secret), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  const s = new Uint8Array(await crypto.subtle.sign("HMAC", k, new TextEncoder().encode(msg)));
  return Array.from(s).map((b) => b.toString(16).padStart(2, "0")).join("");
}
export function safeEq(a: string, b: string) {
  if (a.length !== b.length) return false;
  let r = 0; for (let i = 0; i < a.length; i++) r |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return r === 0;
}
export async function rest(path: string, init: RequestInit = {}) {
  return fetch(SB + "/rest/v1/" + path, { ...init, headers: { ...svc, ...(init.headers || {}) } });
}
export async function settings(): Promise<Record<string, any>> {
  const r = await rest("rpc/public_settings", { method: "POST", body: "{}" });
  return r.ok ? await r.json() : {};
}
