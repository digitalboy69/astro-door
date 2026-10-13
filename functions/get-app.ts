// get-app: returns the customer app only to signed-in members whose access is valid. The app file lives in a PRIVATE bucket.
import { SB, SRK, cors, json, userFrom, rest } from "./_common.ts";
let cache: { t: number; html: string } | null = null;

async function loadApp(): Promise<string> {
  if (cache && Date.now() - cache.t < 60000) return cache.html;
  const r = await fetch(SB + "/storage/v1/object/app/current.html", { headers: { apikey: SRK, Authorization: "Bearer " + SRK } });
  if (!r.ok) throw new Error("storage " + r.status);
  const html = await r.text();
  cache = { t: Date.now(), html };
  return html;
}

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response(null, { status: 204, headers: cors });
  const user = await userFrom(req);
  if (!user) return json({ reason: "login" }, 401);
  const m = await rest("member_access?user_id=eq." + user.id + "&select=status,expires_at,plan,features");
  const row = (m.ok ? await m.json() : [])[0];
  if (!row) return json({ reason: "no_record" }, 403);
  if (row.status === "blocked") return json({ reason: "blocked" }, 403);
  if (row.status !== "active") return json({ reason: "not_paid" }, 402);
  if (row.expires_at && new Date(row.expires_at).getTime() < Date.now()) return json({ reason: "expired" }, 402);
  let html: string;
  try { html = await loadApp(); } catch (e) { return json({ reason: "unavailable", detail: String(e) }, 503); }
  const b = await rest("brand_profiles?user_id=eq." + user.id + "&select=brand_name,tagline,phone,accent,logo");
  const brand = (b.ok ? await b.json() : [])[0] || {};
  const boot = "<script>window.__VAX_BRAND=" + JSON.stringify(brand).replace(/</g, "\\u003c") + ";window.__VAX_FEATURES=" + JSON.stringify(row.features || {}).replace(/</g, "\\u003c") + ";window.__VAX_PLAN=" + JSON.stringify({ plan: row.plan, expires_at: row.expires_at }).replace(/</g, "\\u003c") + ";</script>";
  const i = html.search(/<head[^>]*>/i);
  const out = i >= 0 ? html.replace(/<head[^>]*>/i, (h) => h + boot) : boot + html;
  return new Response(out, { headers: { ...cors, "Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store" } });
});
