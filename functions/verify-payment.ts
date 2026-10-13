// verify-payment: browser sends Razorpay's three values; we check the signature with the secret, then activate.
import { cors, json, userFrom, rest, hmacHex, safeEq } from "./_common.ts";
const KEY_SECRET = Deno.env.get("RAZORPAY_KEY_SECRET") || "";

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response(null, { status: 204, headers: cors });
  if (!KEY_SECRET) return json({ error: "payments_not_configured" }, 503);
  const user = await userFrom(req);
  if (!user) return json({ error: "login" }, 401);
  let b: any; try { b = await req.json(); } catch { return json({ error: "bad_request" }, 400); }
  const oid = String(b.razorpay_order_id || ""), pid = String(b.razorpay_payment_id || ""), sig = String(b.razorpay_signature || "");
  if (!oid || !pid || !sig) return json({ error: "bad_request" }, 400);
  const expect = await hmacHex(KEY_SECRET, oid + "|" + pid);
  if (!safeEq(expect, sig)) return json({ error: "bad_signature" }, 400);
  const p = await rest("payments?order_id=eq." + encodeURIComponent(oid) + "&select=user_id");
  const row = (p.ok ? await p.json() : [])[0];
  if (!row || row.user_id !== user.id) return json({ error: "not_your_order" }, 403);
  const a = await rest("rpc/activate_payment", { method: "POST", body: JSON.stringify({ p_order: oid, p_payment: pid }) });
  if (!a.ok) return json({ error: "db" }, 500);
  return json(await a.json());
});
